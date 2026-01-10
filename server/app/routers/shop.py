from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import os
import json
import sqlite3
from datetime import datetime
from app.routers.auth import verify_init_data
from app.utils.rate_limit import buy_gift_rate_limiter, get_shop_gifts_rate_limiter
from app.utils.balance import get_user_balance
from app.utils.shop_cache import get_cached_shop_gifts, invalidate_shop_cache, update_cached_gift
from app.utils.redis_models import RedisUser
from app.utils.database import get_db_connection, DB_PATH
from app.utils.error_logger import send_error_log

router = APIRouter(prefix="/api", tags=["shop"])

def sanitize_error(error: Exception) -> str:
    """
    Фильтрует технические детали ошибок, чтобы не отдавать структуру БД пользователям
    """
    error_str = str(error).lower()
    
    # Список технических слов, которые указывают на внутренние ошибки
    technical_keywords = [
        'table', 'column', 'sqlite', 'sql', 'database', 
        'syntax', 'constraint', 'foreign key', 'primary key',
        'insert', 'update', 'delete', 'select', 'from', 'where'
    ]
    
    # Если ошибка содержит технические детали - возвращаем общее сообщение
    if any(keyword in error_str for keyword in technical_keywords):
        return "Произошла ошибка при обработке запроса"
    
    # Если это обычная ошибка - возвращаем как есть
    return str(error)

class ShopGift(BaseModel):
    gift_id: str
    slug: Optional[str] = None  # Нужен для покупки и отображения
    title: str
    model_name: Optional[str] = None
    model_path: Optional[str] = None
    symbol_name: Optional[str] = None
    backdrop_name: Optional[str] = None
    center_color: Optional[str] = None
    edge_color: Optional[str] = None
    price: int
    rarity_model: Optional[int] = None
    rarity_symbol: Optional[int] = None
    rarity_backdrop: Optional[int] = None

class BuyGiftRequest(BaseModel):
    initData: str
    slug: str

class GetShopGiftsRequest(BaseModel):
    initData: str

@router.post("/shop/gifts", response_model=List[ShopGift])
async def get_shop_gifts(request: GetShopGiftsRequest):
    """
    Получить список подарков для магазина (исключая те, что в инвентаре)
    """
    # Проверяем initData
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    # Rate limiting: 10 запросов в 20 секунд
    allowed, remaining_time = get_shop_gifts_rate_limiter.is_allowed(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429, 
            detail=f"Слишком частые запросы. Попробуйте через {remaining_time} секунд"
        )
    
    try:
        # Получаем инвентарь пользователя
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        user_result = cursor.fetchone()
        conn.close()
        
        inventory_slugs = []
        if user_result and user_result[0]:
            try:
                raw_inv = json.loads(user_result[0])
                # Support mixed format (strings and objects)
                for item in raw_inv:
                    if isinstance(item, dict):
                        inventory_slugs.append(item.get('slug'))
                    else:
                        inventory_slugs.append(item)
            except:
                inventory_slugs = []
        
        # Получаем подарки с ценами из кэша (ton_price из SQLite, stars_price пересчитана)
        all_gifts = get_cached_shop_gifts()
        
        # Получаем список уже проданных подарков (для глобальной уникальности)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT slug FROM sold_gifts")
        sold_slugs = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Фильтруем: убираем те, что в инвентаре ИЛИ уже проданы кому-то ещё
        gifts = []
        print(f"[DEBUG_SHOP] User {user_id} Inventory: {len(inventory_slugs)} items")
        print(f"[DEBUG_SHOP] Global Sold: {len(sold_slugs)} items")
        
        for gift in all_gifts:
            slug = gift.get('slug')
            # Debug why skipped
            if slug and slug in inventory_slugs:
                print(f"[DEBUG_SHOP] Skipped {slug}: In user inventory")
                continue
            if slug and slug in sold_slugs:
                print(f"[DEBUG_SHOP] Skipped {slug}: In sold_gifts")
                continue
            # if gift['available_amount'] <= 0:
            #     print(f"[DEBUG_SHOP] Skipped {slug}: Available amount {gift['available_amount']}")
            #     continue
                
            gifts.append(ShopGift(**gift))
        
        print(f"[DEBUG_SHOP] Returning {len(gifts)} gifts to user")
        return gifts
        
    except Exception as e:
        print(f"Error fetching shop gifts: {e}")
        await send_error_log(e, "shop.py: get_shop_gifts")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.get("/shop/gift/{gift_id}")
async def get_gift_details(gift_id: str):
    """Получить детали конкретного подарка"""
    try:
        conn = get_db_connection()
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM shop_gifts WHERE gift_id = ?", (gift_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Gift not found")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching gift details: {e}")
        await send_error_log(e, "shop.py: get_gift_details")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/shop/buy-gift")
async def buy_gift(request: BuyGiftRequest):
    """Купить подарок из магазина"""
    # Проверка и валидация initData
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    username = user_data.get('username', '')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем подарок по slug
        cursor.execute("""
            SELECT gift_id, title, price, available_amount, slug, ton_price 
            FROM shop_gifts 
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден")
        
        gift_id, title, price, available_amount, slug, ton_price = gift
        
        # Если price = 0, конвертируем из ton_price (используем ту же формулу что и shop_cache)
        if not price or price <= 0:
            if ton_price and ton_price > 0:
                from app.utils.shop_cache import get_ton_price_usd, get_shop_commission, calculate_stars_price
                ton_usd = get_ton_price_usd()
                commission = get_shop_commission()
                price = calculate_stars_price(ton_price, ton_usd, commission)
                print(f"🛒 [BUY] Calculated price: ton_price={ton_price}, ton_usd={ton_usd}, commission={commission}%, price={price}")
            else:
                conn.close()
                raise HTTPException(status_code=400, detail="Цена подарка не установлена")
        
        # Проверяем доступность
        if available_amount <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок закончился")
        
        # Получаем или создаем пользователя (по полю id, а не user_id!)
        cursor.execute("SELECT balance, inventory FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Создаем пользователя если его нет (безопасно - после валидации initData)
            cursor.execute("""
                INSERT INTO users (id, user_id, username, creation_date, balance, inventory, is_banned)
                VALUES (?, ?, ?, ?, 0, '[]', 0)
            """, (user_id, user_id, username, datetime.now().isoformat()))
            conn.commit()
            
            balance = 0
            inventory_json = '[]'
        else:
            balance, inventory_json = user
        
        # Проверяем баланс
        print(f"🛒 [BUY] User {user_id}: balance={balance}, price={price}, type_balance={type(balance)}, type_price={type(price)}")
        if balance < price:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Недостаточно звезд. Нужно: {price}⭐, есть: {balance}⭐")
        
        # Парсим инвентарь (поддержка старого и нового формата)
        try:
            inventory = json.loads(inventory_json) if inventory_json else []
        except:
            inventory = []
            
        # Проверка наличия (для slug)
        current_slugs = []
        for item in inventory:
            if isinstance(item, dict):
                current_slugs.append(item.get('slug'))
            else:
                current_slugs.append(item)
                
        if slug in current_slugs:
            conn.close()
            raise HTTPException(status_code=400, detail="У вас уже есть этот подарок")

        # --- PAYMENT & LOCK LOGIC ---
        # Проверяем общую сумму пополнений для определения блокировки
        cursor.execute("SELECT SUM(amount) FROM payments WHERE user_id = ? AND type = 'income'", (user_id,))
        total_income_result = cursor.fetchone()
        total_income = total_income_result[0] if total_income_result and total_income_result[0] else 0
        
        # Если пополнений меньше 6767, ставим лок на 72 часа
        unlock_at = None
        if total_income < 6767:
            from datetime import timedelta
            unlock_at = (datetime.now() + timedelta(hours=72)).isoformat()
            print(f"🔒 User {user_id} total income {total_income} < 6767. Gift {slug} locked until {unlock_at}")
        
        # Добавляем в инвентарь как объект
        inventory.append({
            "slug": slug,
            "bought_at": datetime.now().isoformat(),
            "unlock_at": unlock_at,
            "price": price
        })
        
        # Log expense to payments
        cursor.execute("""
            INSERT INTO payments (user_id, amount, method, is_promo, type, date)
            VALUES (?, ?, 'shop', 0, 'expense', ?)
        """, (user_id, price, datetime.now().isoformat()))
        
        # КРИТИЧНО: Используем транзакцию и блокировку для избежания двойной покупки
        try:
            # Блокируем строку подарка для обновления
            # cursor.execute("BEGIN IMMEDIATE") # Already in transaction due to previous INSERT
            
            # Проверяем доступность еще раз с блокировкой
            cursor.execute("""
                SELECT available_amount 
                FROM shop_gifts 
                WHERE slug = ? AND available_amount > 0
            """, (request.slug,))
            
            current_amount = cursor.fetchone()
            
            if not current_amount or current_amount[0] <= 0:
                conn.rollback()
                conn.close()
                raise HTTPException(status_code=400, detail="Подарок уже куплен кем-то другим")
            
            # Обновляем баланс и инвентарь
            new_balance = balance - price
            print(f"🛒 [BUY] Updating balance: {balance} - {price} = {new_balance}")
            cursor.execute("""
                UPDATE users 
                SET balance = ?, inventory = ? 
                WHERE id = ?
            """, (new_balance, json.dumps(inventory), user_id))
            print(f"🛒 [BUY] Rows affected: {cursor.rowcount}")
            
            # Уменьшаем available_amount
            cursor.execute("""
                UPDATE shop_gifts 
                SET available_amount = available_amount - 1 
                WHERE slug = ?
            """, (request.slug,))
            
            # Записываем в таблицу проданных подарков (для глобальной уникальности)
            # STRICT INSERT: will fail if slug already exists (race condition protection)
            try:
                cursor.execute("""
                    INSERT INTO sold_gifts (slug, user_id, purchased_at)
                    VALUES (?, ?, ?)
                """, (slug, user_id, datetime.now().isoformat()))
            except sqlite3.IntegrityError:
                conn.rollback()
                conn.close()
                raise HTTPException(status_code=409, detail="Подарок только что был куплен другим пользователем")
            
            conn.commit()
            
            # Record global sale
            try:
                # Re-open for global sale record (keep main transaction clean or include inside? Including inside is better but conn closed above)
                # Wait, conn.commit() closed the transaction but conn object is still open? 
                # No, conn.close() call is at line 262.
                # I should insert BEFORE commit.
                pass 
            except:
                pass
            conn.close()
            
            # ВАЖНО: Обновляем кэш Redis точечно (без полной инвалидации)
            # current_amount[0] - это количество ДО покупки (из SELECT FOR UPDATE)
            new_amount = current_amount[0] - 1
            update_cached_gift(slug, new_amount)
            
            RedisUser.invalidate(user_id)  # Инвалидируем кэш пользователя
            print(f"✅ Подарок {title} куплен пользователем {user_id} за {price}⭐, новый баланс: {new_balance}⭐")
            
            return {
                "success": True,
                "message": f"Подарок \"{title}\" куплен!",
                "new_balance": new_balance,
                "gift_slug": slug
            }
        except HTTPException:
            raise
        except Exception as e:
            await send_error_log(e, "shop.py: buy_gift (inner)")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error buying gift: {e}")
        await send_error_log(e, "shop.py: buy_gift (outer)")
        raise HTTPException(status_code=500, detail=sanitize_error(e))
