from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from app.utils.database import get_db_connection, DB_PATH
import asyncio
from datetime import datetime, timedelta
import random
from app.config import BOT_TOKEN, DB_PATH, LOG_BOT_TOKEN, LOGS_ID
from app.config import BOT_TOKEN, DB_PATH, LOG_BOT_TOKEN, LOGS_ID
from app.utils.validate import validate_init_data
from app.utils.rate_limit import spin_rate_limiter
from app.utils.balance import get_user_balance
from app.utils.redis_models import RedisUser
from app.pyrogram_client import get_pyrogram
from app.utils.gift_sender import send_gift_async
from app.utils.error_logger import send_error_log
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = APIRouter(prefix="/api", tags=["game"])

class ValidateRequest(BaseModel):
    initData: str

class SellGiftRequest(BaseModel):
    initData: str
    giftName: str

class WithdrawGiftRequest(BaseModel):
    initData: str
    giftName: str | None = None
    name: str | None = None
    index: int

class ManualWithdrawRequest(BaseModel):
    initData: str
    giftName: str
    index: int

class WithdrawNFTGiftRequest(BaseModel):
    initData: str
    slug: str
    slug: str
    messageId: int | None = None

@router.post("/withdraw-gift")
async def withdraw_gift(request: WithdrawGiftRequest):
    """Вывод подарка из инвентаря - отправка через Telegram"""
    
    # Check settings
    if not RedisSettings.get_bool('withdraw_regular_enabled', True):
         return {"success": False, "message": "Авто-выдача временно отключена"}
    
    # Support both giftName and name
    requested_gift = request.name or request.giftName
    if not requested_gift:
         return {"success": False, "message": "Gift name is required"}

    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Проверяем доступность Pyrogram
        pyrogram_app = get_pyrogram()
        if pyrogram_app is None:
            return {"success": False, "message": "Вывод подарков временно недоступен"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        
        # Проверяем что подарок есть в инвентаре (игнорируем index, ищем по имени)
        # Если есть несколько одинаковых подарков, удаляем первый найденный
        # Проверяем что подарок есть в инвентаре (игнорируем index, ищем по имени)
        # Если есть несколько одинаковых подарков, удаляем первый найденный
        if requested_gift not in inventory:
            print(f"❌ Gift not in inventory: '{requested_gift}' not in {inventory}")
            conn.close()
            return {"success": False, "message": "Gift not found in inventory"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (requested_gift,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря
        inventory.remove(requested_gift)
        
        # Обновляем инвентарь в БД
        cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inventory), user_id))
        conn.commit()
        
        # Инвалидируем Redis кеш
        RedisUser.invalidate(user_id)
        
        conn.close()

        # Отправляем подарок через Pyrogram
        # send_gift_async returns (success, error_msg, is_peer_invalid)
        success, error_msg, is_peer_invalid = await send_gift_async(user_id, gift_id, pyrogram_app)
        
        if success:
            return {"success": True, "message": "Gift sent successfully"}
        else:
            # If sending failed, we should probably add the gift back?
            # For now, following existing pattern, we might lose it if we don't handle rollback.
            # But the requirement is "on error open modal".
            # If backend returns success: False, frontend shows modal.
            return {"success": False, "message": error_msg or "Failed to send gift"}

        
    except Exception as e:
        print(f"Error in withdraw_gift: {e}")
        await send_error_log(e, "game.py: withdraw_gift()")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/test-notification")
async def test_notification(request: ValidateRequest):
    """Тестовый эндпоинт для проверки уведомлений"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "error": "Invalid init data"}
    
    try:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
        
        bot = Bot(token=BOT_TOKEN)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Крутить кейс",
                web_app=WebAppInfo(url="https://shelloch.xyz")
            )]
        ])
        
        await bot.send_message(
            user_id,
            f"🎁 <b>Тест</b>, твой бесплатный кейс уже ждет тебя!",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await bot.session.close()
        return {"success": True, "message": "Notification sent"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/check-spin-available")
async def check_spin_available(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "available": False, "timeLeft": 0}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "available": False, "timeLeft": 0}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"valid": True, "available": True, "timeLeft": 0}
        
        last_spin = datetime.fromisoformat(result[0])
        next_spin = last_spin + timedelta(hours=24)
        now = datetime.now()
        
        if now >= next_spin:
            return {"valid": True, "available": True, "timeLeft": 0}
        
        time_left = int((next_spin - now).total_seconds())
        return {"valid": True, "available": False, "timeLeft": time_left}
    except Exception as e:
        return {"valid": False, "available": False, "timeLeft": 0}

@router.post("/spin")
async def spin(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Rate limit: 1 запрос в 5 секунд
        allowed, remaining_time = spin_rate_limiter.is_allowed(user_id)
        if not allowed:
            return {"success": False, "message": f"Попробуйте через {remaining_time}с"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_spin = datetime.fromisoformat(result[0])
            if datetime.now() < last_spin + timedelta(hours=24):
                conn.close()
                return {"success": False, "message": "Spin not available yet"}
        
        cursor.execute("SELECT gift_name, real_chance, paw_min, paw_max, star_min, star_max FROM gift_chances WHERE mode = 'free_spin'")
        chances = cursor.fetchall()
        
        # Закрываем соединение ПЕРЕД sleep
        conn.close()
        
        total = sum(chance[1] for chance in chances)
        rand = random.uniform(0, total)
        current = 0
        selected_gift = chances[0][0]
        selected_row = chances[0]
        
        for row in chances:
            gift_name, real_chance, paw_min, paw_max, star_min, star_max = row
            current += real_chance
            if rand <= current:
                selected_gift = gift_name
                selected_row = row
                break
        
        # Задержка 3 секунды - даем время показать анимацию "Вы выиграли"
        # ВАЖНО: БД уже закрыта, блокировки нет!
        await asyncio.sleep(3)
        
        # Открываем новое соединение для обновления
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем является ли это лапкой
        if selected_gift == "paw":
            # Используем данные из уже загруженной строки
            paw_min = selected_row[2] if selected_row[2] else 1
            paw_max = selected_row[3] if selected_row[3] else 10
            
            # Генерируем случайное количество лапок
            paw_count = random.randint(paw_min, paw_max)
            
            # Добавляем лапки к bonus_balance (бонусные лапки)
            cursor.execute("SELECT bonus_balance FROM users WHERE id = ?", (user_id,))
            current_bonus = cursor.fetchone()[0] or 0
            new_bonus = current_bonus + paw_count
            
            cursor.execute(
                "UPDATE users SET last_spin_date = ?, bonus_balance = ? WHERE id = ?",
                (datetime.now().isoformat(), new_bonus, user_id)
            )
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            return {
                "success": True, 
                "gift": selected_gift, 
                "paw_count": paw_count,
                **user_balance
            }
        # Проверяем является ли это звездой
        elif selected_gift == "star":
            # Используем данные из уже загруженной строки
            star_min = selected_row[4] if selected_row[4] else 1
            star_max = selected_row[5] if selected_row[5] else 5
            
            # Генерируем случайное количество звезд
            star_count = random.randint(star_min, star_max)
            
            # Добавляем звезды к balance
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0] or 0
            new_balance = current_balance + star_count
            
            cursor.execute(
                "UPDATE users SET last_spin_date = ?, balance = ? WHERE id = ?",
                (datetime.now().isoformat(), new_balance, user_id)
            )
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            return {
                "success": True, 
                "gift": selected_gift, 
                "star_count": star_count,
                **user_balance
            }
        else:
            # Для остальных подарков - добавляем в инвентарь
            cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
            inv_result = cursor.fetchone()
            inventory = json.loads(inv_result[0]) if inv_result and inv_result[0] else []
            
            inventory.append(selected_gift)
            
            cursor.execute(
                "UPDATE users SET last_spin_date = ?, inventory = ? WHERE id = ?",
                (datetime.now().isoformat(), json.dumps(inventory), user_id)
            )
            conn.commit()
            conn.close()
            
            # Инвалидируем Redis кеш
            RedisUser.invalidate(user_id)
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            return {
                "success": True, 
                "gift": selected_gift,
                **user_balance
            }
    except Exception as e:
        print(f"Error in spin: {e}")
        await send_error_log(e, "game.py: spin()")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/bazmin-spin")
async def bazmin_spin(request: ValidateRequest):
    print(f"[BAZMIN-SPIN] Request received")
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    print(f"[BAZMIN-SPIN] Validation result: {is_valid}")
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Rate limit: 1 запрос в 5 секунд
        allowed, remaining_time = spin_rate_limiter.is_allowed(user_id)
        if not allowed:
            return {"success": False, "message": f"Попробуйте через {remaining_time}с"}
        
        print(f"[BAZMIN-SPIN] User ID: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем баланс звезд - колонка balance
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            print(f"[BAZMIN-SPIN] User {user_id} not found in database")
            return {"success": False, "message": "User not found"}
        
        balance = result[0] or 0
        print(f"[BAZMIN-SPIN] User {user_id} balance: {balance}")
        
        # Проверяем хватает ли звезд
        if balance < 5:
            conn.close()
            print(f"[BAZMIN-SPIN] Insufficient balance: {balance} < 5")
            return {"success": False, "message": "Недостаточно звезд", "needTopUp": True}
        
        # Списываем 5 звезд сразу
        new_balance = balance - 5
        print(f"[BAZMIN-SPIN] Deducting 5 stars, new balance: {new_balance}")
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()
        
        # Получаем шансы из таблицы gift_chances для режима bazmin
        cursor.execute("SELECT gift_name, real_chance FROM gift_chances WHERE mode = 'bazmin'")
        chances = cursor.fetchall()
        print(f"[BAZMIN-SPIN] Found {len(chances)} gifts for bazmin")
        
        total = sum(chance[1] for chance in chances)
        rand = random.uniform(0, total)
        current = 0
        selected_gift = chances[0][0]
        
        for gift_name, chance in chances:
            current += chance
            if rand <= current:
                selected_gift = gift_name
                break
        
        # Проверяем является ли это лапкой
        if selected_gift == "paw":
            cursor.execute("SELECT paw_min, paw_max FROM gift_chances WHERE gift_name = ? AND mode = 'bazmin'", (selected_gift,))
            paw_range = cursor.fetchone()
            paw_min = paw_range[0] if paw_range and paw_range[0] else 1
            paw_max = paw_range[1] if paw_range and paw_range[1] else 10
            
            paw_count = random.randint(paw_min, paw_max)
            
            # Добавляем лапки в bonus_balance (а не в balance который для звезд)
            cursor.execute("SELECT bonus_balance FROM users WHERE id = ?", (user_id,))
            current_bonus = cursor.fetchone()[0] or 0
            new_bonus = current_bonus + paw_count
            
            cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus, user_id))
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            print(f"[BAZMIN-SPIN] User {user_id} won {paw_count} paws, new bonus_balance: {new_bonus}")
            return {
                "success": True, 
                "gift": selected_gift, 
                "paw_count": paw_count,
                **user_balance
            }
        
        # Проверяем является ли это звездой
        elif selected_gift == "star":
            cursor.execute("SELECT star_min, star_max FROM gift_chances WHERE gift_name = ? AND mode = 'bazmin'", (selected_gift,))
            star_range = cursor.fetchone()
            star_min = star_range[0] if star_range and star_range[0] else 1
            star_max = star_range[1] if star_range and star_range[1] else 5
            
            star_count = random.randint(star_min, star_max)
            
            # Добавляем звезды к уже списанному балансу (возврат звезд)
            final_balance = new_balance + star_count
            
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (final_balance, user_id))
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            print(f"[BAZMIN-SPIN] User {user_id} won {star_count} stars, new balance: {final_balance}")
            return {
                "success": True, 
                "gift": selected_gift, 
                "star_count": star_count,
                **user_balance
            }
        
        else:
            # Для остальных подарков - добавляем в инвентарь
            cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
            inv_result = cursor.fetchone()
            inventory = json.loads(inv_result[0]) if inv_result and inv_result[0] else []
            
            inventory.append(selected_gift)
            
            cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inventory), user_id))
            conn.commit()
            conn.close()
            
            # Инвалидируем Redis кеш
            RedisUser.invalidate(user_id)
            
            return {"success": True, "gift": selected_gift}
    except Exception as e:
        print(f"Error in bazmin-spin: {e}")
        await send_error_log(e, "game.py: bazmin_spin()")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/lapik-spin")
async def lapik_spin(request: ValidateRequest):
    print(f"[LAPIK-SPIN] Request received")
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    print(f"[LAPIK-SPIN] Validation result: {is_valid}")
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Rate limit: 1 запрос в 5 секунд
        allowed, remaining_time = spin_rate_limiter.is_allowed(user_id)
        if not allowed:
            return {"success": False, "message": f"Попробуйте через {remaining_time}с"}
        
        print(f"[LAPIK-SPIN] User ID: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем баланс лапок - колонка bonus_balance
        cursor.execute("SELECT bonus_balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            print(f"[LAPIK-SPIN] User {user_id} not found in database")
            return {"success": False, "message": "User not found"}
        
        bonus_balance = result[0] or 0
        print(f"[LAPIK-SPIN] User {user_id} bonus_balance: {bonus_balance}")
        
        # Проверяем хватает ли лапок
        if bonus_balance < 10:
            conn.close()
            print(f"[LAPIK-SPIN] Insufficient bonus_balance: {bonus_balance} < 10")
            return {"success": False, "message": "Недостаточно лапок"}
        
        # Списываем 10 лапок сразу
        new_bonus_balance = bonus_balance - 10
        print(f"[LAPIK-SPIN] Deducting 10 paws, new bonus_balance: {new_bonus_balance}")
        cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus_balance, user_id))
        conn.commit()
        
        # Получаем шансы из таблицы gift_chances для режима lapik
        cursor.execute("SELECT gift_name, real_chance FROM gift_chances WHERE mode = 'lapik'")
        chances = cursor.fetchall()
        print(f"[LAPIK-SPIN] Found {len(chances)} gifts for lapik")
        
        total = sum(chance[1] for chance in chances)
        rand = random.uniform(0, total)
        cumulative = 0
        selected_gift = None
        
        for gift_name, chance in chances:
            cumulative += chance
            if rand <= cumulative:
                selected_gift = gift_name
                break
        
        # Проверяем является ли это звездой
        if selected_gift == "star":
            cursor.execute("SELECT star_min, star_max FROM gift_chances WHERE gift_name = ? AND mode = 'lapik'", (selected_gift,))
            star_range = cursor.fetchone()
            star_min = star_range[0] if star_range and star_range[0] else 1
            star_max = star_range[1] if star_range and star_range[1] else 4
            
            star_count = random.randint(star_min, star_max)
            
            # Добавляем звезды
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0] or 0
            final_balance = current_balance + star_count
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (final_balance, user_id))
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            print(f"[LAPIK-SPIN] User {user_id} won {star_count} stars, new balance: {final_balance}")
            return {
                "success": True, 
                "gift": selected_gift, 
                "star_count": star_count,
                **user_balance
            }
        
        else:
            # Добавляем подарок в инвентарь
            cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
            inv_result = cursor.fetchone()
            inventory = json.loads(inv_result[0]) if inv_result and inv_result[0] else []
            
            inventory.append(selected_gift)
            
            cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inventory), user_id))
            conn.commit()
            conn.close()
            
            # Инвалидируем Redis кеш
            RedisUser.invalidate(user_id)
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            
            return {
                "success": True, 
                "gift": selected_gift,
                **user_balance
            }
    except Exception as e:
        print(f"Error in lapik-spin: {e}")
        await send_error_log(e, "game.py: lapik_spin()")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/get-inventory")
async def get_inventory(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "inventory": []}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "inventory": []}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        inventory = json.loads(result[0]) if result and result[0] else []
        return {"valid": True, "inventory": inventory}
    except Exception:
        return {"valid": False, "inventory": []}

@router.post("/sell-gift")
async def sell_gift(request: SellGiftRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT inventory, balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        balance = result[1] or 0
        
        # Находим первый экземпляр подарка в инвентаре
        try:
            gift_index = inventory.index(request.giftName)
        except ValueError:
            conn.close()
            return {"success": False, "message": "Gift not found in inventory"}
        
        # Получаем цену из базы данных
        cursor.execute("SELECT price, gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        price_result = cursor.fetchone()
        
        if not price_result:
            conn.close()
            return {"success": False, "message": "Price not found"}
        
        price = price_result[0]
        gift_id = price_result[1] if len(price_result) > 1 else None
        
        # Удаляем подарок из инвентаря
        inventory.pop(gift_index)
        
        # Обновляем баланс
        new_balance = balance + price
        
        cursor.execute(
            "UPDATE users SET inventory = ?, balance = ? WHERE id = ?",
            (json.dumps(inventory), new_balance, user_id)
        )
        conn.commit()
        conn.close()
        
        # Инвалидируем Redis кеш
        RedisUser.invalidate(user_id)
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        
        return {
            "success": True, 
            "newBalance": new_balance, 
            "price": price,
            **user_balance
        }
    except Exception as e:
        await send_error_log(e, "game.py: sell_gift()")
        return {"success": False, "message": str(e)}

# ENDPOINT УДАЛЕН - баланс теперь возвращается во всех операциях через get_user_balance()

@router.post("/get-prices")
async def get_prices(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "prices": {}}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, price FROM gift_prices")
        results = cursor.fetchall()
        conn.close()
        
        prices = {gift_name: price for gift_name, price in results}
        return {"valid": True, "prices": prices}
    except Exception as e:
        return {"valid": False, "prices": {}}

@router.post("/check-withdraw-available")
async def check_withdraw_available(request: ValidateRequest):
    """Проверка доступности функции вывода подарков"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "available": False}
    
    pyrogram_app = get_pyrogram()
    return {"valid": True, "available": pyrogram_app is not None}

@router.post("/withdraw-gift")
async def withdraw_gift(request: WithdrawGiftRequest):
    """Вывод подарка из инвентаря - отправка через Telegram"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Проверяем доступность Pyrogram
        pyrogram_app = get_pyrogram()
        if pyrogram_app is None:
            return {"success": False, "message": "Вывод подарков временно недоступен"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        
        # Проверяем что подарок есть в инвентаре (игнорируем index, ищем по имени)
        requested_gift = request.giftName
        if requested_gift not in inventory:
            print(f"❌ Gift not in inventory: '{requested_gift}' not in {inventory}")
            conn.close()
            return {"success": False, "message": "Gift not found in inventory"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря по имени (первое вхождение)
        inventory.remove(requested_gift)
        
        cursor.execute(
            "UPDATE users SET inventory = ? WHERE id = ?",
            (json.dumps(inventory), user_id)
        )
        conn.commit()
        
        # Инвалидируем Redis кеш
        RedisUser.invalidate(user_id)
        
        # ПОТОМ отправляем подарок через Pyrogram
        send_success, error_msg, is_peer_invalid = await send_gift_async(user_id, gift_id, pyrogram_app)
        
        if not send_success:
            # Возвращаем подарок обратно в инвентарь
            inventory.append(requested_gift)
            cursor.execute(
                "UPDATE users SET inventory = ? WHERE id = ?",
                (json.dumps(inventory), user_id)
            )
            conn.commit()
            conn.close()
            
            # Инвалидируем Redis кеш (вернули подарок)
            RedisUser.invalidate(user_id)
            
            # Если ошибка PeerIdInvalid - отправляем уведомление через основной бот
            if is_peer_invalid:
                try:
                    bot = Bot(token=BOT_TOKEN)
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🔄 Попробовать ещё раз", callback_data=f"retry_gift:{user_id}:{requested_gift}"),
                            InlineKeyboardButton(text="❓ Помощь", callback_data=f"help_gift:{user_id}:{requested_gift}")
                        ]
                    ])
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "❌ <b>Ошибка отправки подарка</b>\n\n"
                            "Не удалось отправить подарок. Убедитесь, что вы начали чат с ботом "
                            "@shellrelayer и попробуйте ещё раз.\n\n"
                            f"🎁 Подарок: <b>{requested_gift}</b>"
                        ),
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    await bot.session.close()
                except Exception as bot_error:
                    print(f"Error sending PeerIdInvalid notification: {bot_error}")
            
            return {
                "success": False, 
                "message": "Подарок не отправился из-за ошибки",
                "error": error_msg or "Неизвестная ошибка",
                "needsManual": True,
                "isPeerInvalid": is_peer_invalid
            }
        
        conn.close()
        return {"success": True, "message": "Подарок успешно отправлен!"}
    except Exception as e:
        print(f"Error in withdraw_gift: {e}")
        await send_error_log(e, "game.py: withdraw_gift()")
        # При любой ошибке соединение может быть уже закрыто
        try:
            conn.close()
        except:
            pass
        return {"success": False, "message": "Ошибка сервера", "error": str(e)}

@router.post("/request-manual-withdraw")
async def request_manual_withdraw(request: ManualWithdrawRequest):
    """Запрос ручной выдачи подарка администрацией"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        username = user.get('username', '')
        first_name = user.get('first_name', 'User')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        
        # Проверяем что подарок есть в инвентаре (игнорируем index, ищем по имени)
        requested_gift = request.giftName
        if requested_gift not in inventory:
            print(f"❌ Gift not in inventory (sell): '{requested_gift}' not in {inventory}")
            conn.close()
            return {"success": False, "message": "Gift not found in inventory"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря по имени (первое вхождение)
        inventory.remove(requested_gift)
        
        cursor.execute(
            "UPDATE users SET inventory = ? WHERE id = ?",
            (json.dumps(inventory), user_id)
        )
        conn.commit()
        conn.close()
        
        # Отправляем запрос в канал логов (если настроен)
        if not LOG_BOT_TOKEN or not LOGS_ID:
            return {"success": True, "message": "Запрос отправлен администрации (уведомление в разработке)"}
        
        log_bot = Bot(token=LOG_BOT_TOKEN)
        
        user_link = f"@{username}" if username else first_name
        user_mention = f'<a href="tg://user?id={user_id}">{user_link}</a>'
        
        text = f"""🎁 <b>Запрос на ручную выдачу подарка</b>

👤 Пользователь: {user_mention}
🆔 ID: <code>{user_id}</code>
🎁 Подарок: {request.giftName}
🔑 Gift ID: <code>{gift_id}</code>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_gift_{user_id}_{gift_id}")]
        ])
        
        await log_bot.send_message(LOGS_ID, text, parse_mode="HTML", reply_markup=keyboard)
        await log_bot.session.close()
        
        # Отправляем уведомление пользователю
        try:
            main_bot = Bot(token=BOT_TOKEN)
            await main_bot.send_message(
                user_id, 
                "✅ Ваш запрос на выдачу подарка отправлен администрации. Подарок будет отправлен в течение 24 часов."
            )
            await main_bot.session.close()
        except Exception as e:
            print(f"Failed to send notification to user {user_id}: {e}")
        
        return {"success": True, "message": "Запрос отправлен администрации"}
    except Exception as e:
        print(f"Error in request_manual_withdraw: {e}")
        return {"success": False, "message": "Ошибка сервера", "error": str(e)}

@router.post("/get-nft-gifts")
async def get_nft_gifts(request: ValidateRequest):
    """Получение NFT подарков из Telegram"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "gifts": []}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "gifts": []}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Получаем подарки через Pyrogram
        app = get_pyrogram()
        gifts_list = []
        
        try:
            async for gift in app.get_chat_gifts(
                chat_id=user_id,
                exclude_unlimited=True,
                limit=50
            ):
                # Извлекаем данные о владельце и отправителе
                owner = None
                from_user = None
                
                if hasattr(gift, 'owner') and gift.owner:
                    owner = {
                        'id': gift.owner.id,
                        'username': getattr(gift.owner, 'username', None),
                        'first_name': getattr(gift.owner, 'first_name', ''),
                        'last_name': getattr(gift.owner, 'last_name', ''),
                        'photo_url': None
                    }
                    # Получаем URL аватарки
                    if hasattr(gift.owner, 'photo') and gift.owner.photo:
                        try:
                            photo = await app.download_media(gift.owner.photo.big_file_id, in_memory=True)
                            # В реальности нужно сохранить фото и отдать URL, пока просто оставим None
                        except:
                            pass
                
                if hasattr(gift, 'from_user') and gift.from_user:
                    from_user = {
                        'id': gift.from_user.id,
                        'username': getattr(gift.from_user, 'username', None),
                        'first_name': getattr(gift.from_user, 'first_name', ''),
                        'last_name': getattr(gift.from_user, 'last_name', ''),
                        'photo_url': None
                    }
                    if hasattr(gift.from_user, 'photo') and gift.from_user.photo:
                        try:
                            photo = await app.download_media(gift.from_user.photo.big_file_id, in_memory=True)
                        except:
                            pass
                
                # Извлекаем атрибуты
                model_name = None
                symbol_name = None
                backdrop_name = None
                rarity_model = None
                rarity_symbol = None
                rarity_backdrop = None
                
                if hasattr(gift, 'attributes') and gift.attributes:
                    for attr in gift.attributes:
                        attr_type = str(getattr(attr, 'type', ''))
                        attr_name = getattr(attr, 'name', '')
                        
                        # Пропускаем ORIGINAL_DETAILS (комментарии к подаркам)
                        if 'ORIGINAL_DETAILS' in attr_type:
                            continue
                        
                        if 'MODEL' in attr_type:
                            model_name = attr_name
                            rarity_model = getattr(attr, 'rarity', 0)
                        elif 'SYMBOL' in attr_type:
                            symbol_name = attr_name
                            rarity_symbol = getattr(attr, 'rarity', 0)
                        elif 'BACKDROP' in attr_type:
                            backdrop_name = attr_name
                            rarity_backdrop = getattr(attr, 'rarity', 0)
                
                gift_data = {
                    'id': str(gift.id),
                    'title': getattr(gift, 'title', ''),
                    'name': getattr(gift, 'name', ''),
                    'collectible_id': getattr(gift, 'collectible_id', 0),
                    'model_name': model_name,
                    'symbol_name': symbol_name,
                    'backdrop_name': backdrop_name,
                    'rarity_model': rarity_model,
                    'rarity_symbol': rarity_symbol,
                    'rarity_backdrop': rarity_backdrop,
                    'owner': owner,
                    'from_user': from_user,
                    'transfer_price': getattr(gift, 'transfer_price', 0),
                    'can_export_at': str(getattr(gift, 'can_export_at', ''))
                }
                
                gifts_list.append(gift_data)
        except Exception as e:
            print(f"Error getting gifts from Telegram: {e}")
            import traceback
            traceback.print_exc()
        
        return {"valid": True, "gifts": gifts_list}
        
    except Exception as e:
        print(f"Error in get_nft_gifts: {e}")
        import traceback
        traceback.print_exc()
        return {"valid": True, "gifts": []}

@router.post("/withdraw-nft-gift")
async def withdraw_nft_gift(request: WithdrawNFTGiftRequest):
    """Вывод NFT подарка через Client.transfer_gift()"""
    
    # Check settings
    if not RedisSettings.get_bool('withdraw_nft_enabled', True):
         return {"success": False, "message": "Авто-выдача временно отключена"}

    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        username = user.get('username', '')
        first_name = user.get('first_name', 'User')
        
        # Проверяем доступность Pyrogram
        pyrogram_app = get_pyrogram()
        if pyrogram_app is None:
            return {"success": False, "message": "Вывод подарков временно недоступен"}
        
        # Получаем подарок через Pyrogram со страницы БОТА ("me")
        gift_found = False
        gift_title = "Unknown"
        found_message_id = None
        
        try:
            # Ищем подарок в профиле бота
            async for gift in pyrogram_app.get_chat_gifts(
                chat_id="me",
                limit=200 # Ищем среди последних 200 подарков
            ):
                # Проверяем slug (name)
                gift_slug = getattr(gift, 'name', None)
                
                # Если нашли подарок с нужным slug
                if gift_slug == request.slug:
                     # Дополнительная проверка: подарок должен принадлежать боту (ну, он и так в профиле)
                     # Но главное - он не должен быть "скрыт" или уже отправлен? 
                     # get_chat_gifts возвращает то что на профиле.
                     # Мы просто берем первый попавшийся подходящий.
                     
                     gift_found = True
                     gift_title = getattr(gift, 'title', 'Unknown')
                     found_message_id = getattr(gift, 'message_id', None)
                     break
            
            if not gift_found or not found_message_id:
                # Если не нашли автоматически - отправляем на ручной вывод
                # Но вернем ошибку, чтобы фронт показал модалку
                return {"success": False, "message": "Подарок не найден в хранилище бота", "error": f"Gift {request.slug} not found in bot inventory"}
            
        except Exception as e:
            print(f"Error checking bot gifts: {e}")
            return {"success": False, "message": "Ошибка проверки хранилища", "error": str(e)}
        
        # Пробуем отправить подарок пользователю
        try:
            await pyrogram_app.transfer_gift(
                message_id=found_message_id,
                to_chat_id=user_id
            )
            
            return {"success": True, "message": "Подарок успешно отправлен!"}
            
        except Exception as transfer_error:
            error_msg = str(transfer_error)
            print(f"Error transferring NFT gift: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Отправляем запрос администрации на ручную выдачу
            if LOG_BOT_TOKEN and LOGS_ID:
                try:
                    log_bot = Bot(token=LOG_BOT_TOKEN)
                    
                    user_link = f"@{username}" if username else first_name
                    user_mention = f'<a href="tg://user?id={user_id}">{user_link}</a>'
                    
                    text = f"""🎁 <b>Ошибка вывода NFT подарка</b>

👤 Пользователь: {user_mention}
🆔 ID: <code>{user_id}</code>
🎁 Подарок: {gift_title}
🔖 Slug: <code>{request.slug}</code>
💬 Message ID: <code>{request.messageId}</code>

❌ Ошибка: <code>{error_msg[:200]}</code>

<i>Требуется ручная отправка подарка пользователю</i>"""
                    
                    await log_bot.send_message(LOGS_ID, text, parse_mode="HTML")
                    await log_bot.session.close()
                    
                    # Уведомляем пользователя
                    try:
                        main_bot = Bot(token=BOT_TOKEN)
                        await main_bot.send_message(
                            user_id, 
                            "⚠️ Возникла ошибка при автоматической отправке подарка.\n\n"
                            "Ваш запрос отправлен администрации. Подарок будет отправлен вручную в течение 24 часов."
                        )
                        await main_bot.session.close()
                    except Exception as notify_error:
                        print(f"Failed to send notification to user {user_id}: {notify_error}")
                    
                except Exception as log_error:
                    print(f"Failed to send log message: {log_error}")
            
            return {
                "success": False, 
                "message": "Не удалось автоматически отправить подарок. Запрос отправлен администрации.",
                "error": error_msg,
                "needsManual": True
            }
            
    except Exception as e:
        print(f"Error in withdraw_nft_gift: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": "Ошибка сервера", "error": str(e)}
