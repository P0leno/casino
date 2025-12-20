from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
import sqlite3
from datetime import datetime
from app.routers.auth import verify_init_data
from app.utils.rate_limit import get_inventory_rate_limiter
from app.utils.balance import get_user_balance
from app.tasks.price_updater import search_tonnel_resale
from app.utils.redis_models import RedisSettings, RedisUser
from app.utils.redis_client import cache
from app.utils.database import get_db_connection, DB_PATH
from app.utils.error_logger import send_error_log

router = APIRouter(prefix="/api", tags=["inventory"])

# Фоны для которых ищем по подарку + фону + модели
SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]

class GetInventoryRequest(BaseModel):
    initData: str

class GetSellPriceRequest(BaseModel):
    initData: str
    slug: str

class SellGiftRequest(BaseModel):
    initData: str
    slug: str

class ManualWithdrawRequest(BaseModel):
    initData: str
    slug: str
    giftTitle: str

class ManualWithdrawNFTRequest(BaseModel):
    initData: str
    slug: str
    giftTitle: str
    messageId: int

def sanitize_error(error: Exception) -> str:
    """
    Фильтрует технические детали ошибок
    """
    error_str = str(error).lower()
    
    technical_keywords = [
        'table', 'column', 'sqlite', 'sql', 'database', 
        'syntax', 'constraint', 'foreign key', 'primary key',
        'insert', 'update', 'delete', 'select', 'from', 'where'
    ]
    
    if any(keyword in error_str for keyword in technical_keywords):
        return "Произошла ошибка при обработке запроса"
    
    return str(error)

def get_ton_to_stars_rate():
    """Получить курс конвертации TON в Stars"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем цену TON в USD
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            ton_price_usd = float(result[0])
            # 1 Star = примерно $0.015 (может меняться)
            # Поэтому 1 TON = ton_price_usd / 0.015 Stars
            stars_per_ton = ton_price_usd / 0.015
            return stars_per_ton
        
        return 366.67  # Дефолт ~5.5 / 0.015
    except Exception as e:
        print(f"Error getting TON to Stars rate: {e}")
        # Async call in sync function? No, this function is sync.
        # But wait, send_error_log is async.
        # If this function is called from async context, we can await it?
        # get_ton_to_stars_rate is sync. It is called from async functions (get_sell_price).
        # We can't await here.
        # We should just print or use logging. Or better, just print as before to avoid converting it to async.
        return 366.67

# Список обычных (не NFT) подарков
REGULAR_GIFTS = ['bear', 'cake', 'cup', 'diamond', 'flowers', 'gift', 'heart', 'ring', 'rocket', 'rose', 'bottle']

@router.post("/inventory/get")
async def get_inventory(request: GetInventoryRequest):
    """Получить инвентарь пользователя с полной информацией о подарках"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    is_admin = RedisSettings.is_admin(user_id)
    
    # Rate limiting: 10 запросов в 200 секунд
    allowed, remaining_time = get_inventory_rate_limiter.is_allowed(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429, 
            detail=f"Слишком частые запросы. Попробуйте через {remaining_time} секунд"
        )
    
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем инвентарь пользователя
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"inventory": [], "isAdmin": is_admin}
        
        inventory_json = result['inventory']
        inventory_items = json.loads(inventory_json) if inventory_json else []
        
        if not inventory_items:
            conn.close()
            return {"inventory": [], "isAdmin": is_admin}
        
        # Получаем комиссию на продажу из Redis
        sell_commission = RedisSettings.get_float('sell_commission', 10.0)
        
        # Разделяем на обычные подарки (по имени) и NFT (по slug)
        regular_gift_names = [item for item in inventory_items if item in REGULAR_GIFTS]
        nft_slugs = [item for item in inventory_items if item not in REGULAR_GIFTS]
        
        inventory_gifts = []
        
        # Получаем обычные подарки из gift_prices
        if regular_gift_names:
            placeholders = ','.join(['?'] * len(regular_gift_names))
            cursor.execute(f"""
                SELECT gift_name, price, gift_id
                FROM gift_prices
                WHERE gift_name IN ({placeholders})
            """, regular_gift_names)
            
            for row in cursor.fetchall():
                gift_name, price, gift_id = row
                
                # Рассчитываем sell_price с комиссией для обычных подарков
                sell_price = None
                if price and price > 0:
                    sell_price = int(price * (1 - sell_commission / 100))
                    sell_price = max(1, sell_price)  # Минимум 1 звезда
                
                # Формируем данные для обычного подарка
                inventory_gifts.append({
                    'gift_id': gift_id,
                    'slug': gift_name,  # Для обычных подарков slug = gift_name
                    'title': gift_name.capitalize(),
                    'model_name': None,
                    'model_path': f"/gifts/{gift_name}.json",  # Путь к Lottie анимации
                    'symbol_name': None,
                    'backdrop_name': None,
                    'center_color': None,
                    'edge_color': None,
                    'pattern_color': None,
                    'text_color': None,
                    'rarity_model': None,
                    'rarity_symbol': None,
                    'rarity_backdrop': None,
                    'ton_price': None,
                    'price': price,
                    'sell_price': sell_price,
                    'is_regular_gift': True
                })
        
        # Получаем NFT подарки из shop_gifts
        if nft_slugs:
            placeholders = ','.join(['?'] * len(nft_slugs))
            cursor.execute(f"""
                SELECT 
                    gift_id, slug, title, model_name, model_path,
                    symbol_name, backdrop_name, center_color, edge_color,
                    pattern_color, text_color, rarity_model, rarity_symbol,
                    rarity_backdrop, ton_price, price
                FROM shop_gifts
                WHERE slug IN ({placeholders})
            """, nft_slugs)
            
            # Получаем курс TON из Redis
            ton_price_usd = RedisSettings.get_float('ton_price_usd', 5.5)
            stars_per_usd = 50  # 50 звезд = 1 USD
            
            for row in cursor.fetchall():
                gift_dict = dict(row)
                gift_dict['is_regular_gift'] = False
                
                # Рассчитываем sell_price с комиссией
                # Сначала пробуем price, если 0 - конвертируем из ton_price
                stars_price = gift_dict['price']
                if (not stars_price or stars_price <= 0) and gift_dict['ton_price']:
                    # Конвертируем TON в звезды: ton_price * ton_usd * stars_per_usd
                    stars_price = int(gift_dict['ton_price'] * ton_price_usd * stars_per_usd)
                    gift_dict['price'] = stars_price  # Обновляем для отображения
                
                if stars_price and stars_price > 0:
                    sell_price = int(stars_price * (1 - sell_commission / 100))
                    gift_dict['sell_price'] = max(1, sell_price)
                else:
                    gift_dict['sell_price'] = None
                
                inventory_gifts.append(gift_dict)
        
        conn.close()
        
        return {"inventory": inventory_gifts, "isAdmin": is_admin}
        
    except Exception as e:
        print(f"Error getting inventory: {e}")
        await send_error_log(e, "inventory.py: get_inventory")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/inventory/get-sell-price")
async def get_sell_price(request: GetSellPriceRequest):
    """Получить цену продажи подарка (с комиссией)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем что подарок в инвентаре пользователя
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        inventory_json = result[0]
        inventory = json.loads(inventory_json) if inventory_json else []
        
        if request.slug not in inventory:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок не найден в инвентаре")
        
        # Получаем информацию о подарке
        cursor.execute("""
            SELECT gift_id, title, model_name, backdrop_name, ton_price
            FROM shop_gifts
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден в базе")
        
        gift_id, title, model_name, backdrop_name, cached_ton_price = gift
        
        # Получаем комиссию на продажу
        cursor.execute("SELECT value FROM settings WHERE key = 'sell_commission'")
        commission_result = cursor.fetchone()
        sell_commission = float(commission_result[0]) if commission_result else 10.0
        
        conn.close()
        
        # Получаем актуальную цену с Tonnel
        print(f"🔍 Поиск цены для: {title} (модель: {model_name}, фон: {backdrop_name})")
        
        search_by_backdrop = backdrop_name and backdrop_name in SPECIAL_BACKDROPS
        
        if search_by_backdrop:
            min_ton_price = await search_tonnel_resale(title, model=model_name, backdrop=backdrop_name)
        else:
            min_ton_price = await search_tonnel_resale(title, model=model_name)
        
        # Если не нашли на Tonnel - используем кешированную цену
        if min_ton_price is None:
            if cached_ton_price:
                min_ton_price = cached_ton_price
                print(f"⚠️  Не найдено на Tonnel, используем кешированную цену: {cached_ton_price} TON")
            else:
                raise HTTPException(status_code=400, detail="Не удалось определить цену подарка")
        else:
            print(f"✅ Найдена цена на Tonnel: {min_ton_price} TON")
        
        # Вычитаем комиссию
        price_after_commission = min_ton_price * (1 - sell_commission / 100)
        
        # Конвертируем в Stars
        stars_per_ton = get_ton_to_stars_rate()
        stars_price = int(price_after_commission * stars_per_ton)
        
        return {
            "slug": request.slug,
            "title": title,
            "ton_price": min_ton_price,
            "commission_percent": sell_commission,
            "ton_price_after_commission": round(price_after_commission, 2),
            "stars_price": stars_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting sell price: {e}")
        await send_error_log(e, "inventory.py: get_sell_price")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/inventory/sell-nft")
@router.post("/inventory/sell")
@router.post("/sell-gift")
@router.post("/shop/sell-gift")
async def sell_gift(request: SellGiftRequest):
    """Продать подарок из инвентаря (работает для всех типов подарков)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    try:
        # Защита от двойной продажи - Redis lock
        lock_key = f"sell_lock:{user_id}"
        if cache.is_available():
            # Проверяем есть ли блокировка
            if cache.client.get(lock_key):
                raise HTTPException(status_code=429, detail="Подождите, предыдущая операция ещё выполняется")
            # Устанавливаем блокировку на 5 секунд
            cache.client.setex(lock_key, 5, "1")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT inventory, balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        inventory_json, balance = result
        inventory = json.loads(inventory_json) if inventory_json else []
        
        # Проверяем что подарок в инвентаре
        if request.slug not in inventory:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок не найден в инвентаре")
        
        # Получаем АКТУАЛЬНУЮ информацию о подарке из БД
        # Сначала ищем в shop_gifts (NFT подарки)
        cursor.execute("""
            SELECT gift_id, title, price, ton_price
            FROM shop_gifts
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        is_nft = gift is not None
        
        # Если не нашли в shop_gifts, ищем в gift_prices (обычные подарки)
        if not gift:
            cursor.execute("""
                SELECT gift_id, gift_name as title, price, NULL as ton_price
                FROM gift_prices
                WHERE gift_name = ?
            """, (request.slug,))
            gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден в базе")
        
        gift_id, title, current_price, ton_price = gift
        
        # Если price = 0, конвертируем из ton_price
        if (not current_price or current_price <= 0) and ton_price and ton_price > 0:
            ton_price_usd = RedisSettings.get_float('ton_price_usd', 5.5)
            stars_per_usd = 50
            current_price = int(ton_price * ton_price_usd * stars_per_usd)
        
        if not current_price or current_price <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Цена подарка не установлена")
        
        # Получаем комиссию из Redis
        sell_commission = RedisSettings.get_float('sell_commission', 10.0)
        
        # Вычисляем цену продажи с комиссией
        stars_price = int(current_price * (1 - sell_commission / 100))
        
        # Удаляем подарок из инвентаря (только первое вхождение)
        inventory.remove(request.slug)
        
        # Обновляем баланс и инвентарь
        new_balance = balance + stars_price
        cursor.execute("""
            UPDATE users 
            SET inventory = ?, balance = ? 
            WHERE id = ?
        """, (json.dumps(inventory), new_balance, user_id))
        
        conn.commit()
        conn.close()
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        
        # Инвалидируем кэш пользователя в Redis
        RedisUser.invalidate(user_id)
        
        print(f"✅ Продан подарок {title} за {stars_price}⭐ (цена: {current_price}⭐, комиссия: {sell_commission}%)")
        
        # Снимаем блокировку
        if cache.is_available():
            cache.client.delete(lock_key)
        
        return {
            "success": True,
            "newBalance": new_balance,
            "newBonusBalance": user_balance.get('bonusBalance', 0)
        }
        
    except HTTPException:
        # Снимаем блокировку при ошибке
        if cache.is_available():
            cache.client.delete(f"sell_lock:{user_id}")
        raise
    except Exception as e:
        # Снимаем блокировку при ошибке
        if cache.is_available():
            cache.client.delete(f"sell_lock:{user_id}")
        print(f"Error selling gift: {e}")
        await send_error_log(e, "inventory.py: sell_gift")
        raise HTTPException(status_code=500, detail=sanitize_error(e))


@router.post("/inventory/manual-withdraw")
async def manual_withdraw(request: ManualWithdrawRequest):
    """Ручной вывод подарка (при ошибке PeerIdInvalid)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    username = user_data.get('username', '')
    
    try:
        # Проверяем есть ли username
        if not username:
            # Нет username - отправляем сообщение в ЛС и возвращаем подарок
            from app.telegram_bot import bot
            try:
                await bot.send_message(
                    user_id,
                    f"❌ Подарок <b>{request.giftTitle}</b> не выведен.\n\n"
                    f"Пожалуйста, установите юзернейм в настройках Telegram и попробуйте снова.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
            
            return {
                "success": False,
                "needsUsername": True,
                "message": "Установите юзернейм в Telegram и попробуйте снова"
            }
        
        # Есть username - удаляем подарок из инвентаря и отправляем заявку в логи
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        inventory = json.loads(result[0] or "[]")
        
        # Удаляем подарок из инвентаря
        if request.slug in inventory:
            inventory.remove(request.slug)
            cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inventory), user_id))
            conn.commit()
        
        conn.close()
        
        # Инвалидируем кэш
        RedisUser.invalidate(user_id)
        
        # Отправляем заявку в логи
        from app.log_bot import log_bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        import os
        
        LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнен", callback_data=f"manual_done_{user_id}_{request.slug}")]
        ])
        
        await log_bot.send_message(
            LOG_CHANNEL_ID,
            f"📦 <b>Ручной вывод подарка</b>\n\n"
            f"🎁 Подарок: <code>{request.giftTitle}</code>\n"
            f"📝 Slug: <code>{request.slug}</code>\n"
            f"👤 Пользователь: @{username}\n"
            f"🆔 ID: <code>{user_id}</code>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        print(f"✅ Manual withdraw request: {request.giftTitle} for @{username} ({user_id})")
        
        return {
            "success": True,
            "message": "Заявка на ручной вывод отправлена администрации"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error manual withdraw: {e}")
        await send_error_log(e, "inventory.py: manual_withdraw")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory/manual-withdraw-nft")
async def manual_withdraw_nft(request: ManualWithdrawNFTRequest):
    """Ручной вывод NFT подарка (при ошибке PeerIdInvalid)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    username = user_data.get('username', '')
    
    try:
        # Проверяем есть ли username
        if not username:
            from app.telegram_bot import bot
            try:
                await bot.send_message(
                    user_id,
                    f"❌ Подарок <b>{request.giftTitle}</b> не выведен.\n\n"
                    f"Пожалуйста, установите юзернейм в настройках Telegram и попробуйте снова.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
            
            return {
                "success": False,
                "needsUsername": True,
                "message": "Установите юзернейм в Telegram и попробуйте снова"
            }
        
        # Есть username - удаляем NFT из purchased_gifts и отправляем заявку
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем что NFT принадлежит пользователю
        cursor.execute("""
            SELECT id FROM purchased_gifts 
            WHERE user_id = ? AND slug = ? AND message_id = ?
        """, (user_id, request.slug, request.messageId))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="NFT подарок не найден")
        
        # Удаляем NFT из purchased_gifts
        cursor.execute("""
            DELETE FROM purchased_gifts 
            WHERE user_id = ? AND slug = ? AND message_id = ?
        """, (user_id, request.slug, request.messageId))
        
        conn.commit()
        conn.close()
        
        # Инвалидируем кэш
        RedisUser.invalidate(user_id)
        
        # Отправляем заявку в логи
        from app.log_bot import log_bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнен", callback_data=f"manual_nft_done_{user_id}_{request.messageId}")]
        ])
        
        await log_bot.send_message(
            LOG_CHANNEL_ID,
            f"📦 <b>Ручной вывод NFT подарка</b>\n\n"
            f"🎁 Подарок: <code>{request.giftTitle}</code>\n"
            f"📝 Slug: <code>{request.slug}</code>\n"
            f"🔢 Message ID: <code>{request.messageId}</code>\n"
            f"👤 Пользователь: @{username}\n"
            f"🆔 ID: <code>{user_id}</code>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        print(f"✅ Manual NFT withdraw request: {request.giftTitle} for @{username} ({user_id})")
        
        return {
            "success": True,
            "message": "Заявка на ручной вывод NFT отправлена администрации"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error manual NFT withdraw: {e}")
        await send_error_log(e, "inventory.py: manual_withdraw_nft")
        raise HTTPException(status_code=500, detail=str(e))
