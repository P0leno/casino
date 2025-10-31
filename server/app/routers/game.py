from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
import random
from app.config import BOT_TOKEN, DB_PATH, LOG_BOT_TOKEN, LOGS_ID
from app.utils import validate_init_data
from app.pyrogram_client import get_pyrogram
from app.utils.gift_sender import send_gift_async
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = APIRouter(prefix="/api", tags=["game"])

class ValidateRequest(BaseModel):
    initData: str

class SellGiftRequest(BaseModel):
    initData: str
    giftName: str
    index: int

class WithdrawGiftRequest(BaseModel):
    initData: str
    giftName: str
    index: int

class ManualWithdrawRequest(BaseModel):
    initData: str
    giftName: str
    index: int

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
        
        conn = sqlite3.connect(DB_PATH)
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_spin = datetime.fromisoformat(result[0])
            if datetime.now() < last_spin + timedelta(hours=24):
                conn.close()
                return {"success": False, "message": "Spin not available yet"}
        
        cursor.execute("SELECT gift_name, real_chance FROM gift_chances")
        chances = cursor.fetchall()
        
        total = sum(chance[1] for chance in chances)
        rand = random.uniform(0, total)
        current = 0
        selected_gift = chances[0][0]
        
        for gift_name, chance in chances:
            current += chance
            if rand <= current:
                selected_gift = gift_name
                break
        
        # Задержка 3 секунды - даем время показать анимацию "Вы выиграли"
        await asyncio.sleep(3)
        
        # Проверяем является ли это лапкой
        if selected_gift == "paw":
            # Получаем диапазон лапок для этого подарка
            cursor.execute("SELECT paw_min, paw_max FROM gift_chances WHERE gift_name = ?", (selected_gift,))
            paw_range = cursor.fetchone()
            paw_min = paw_range[0] if paw_range and paw_range[0] else 1
            paw_max = paw_range[1] if paw_range and paw_range[1] else 10
            
            # Генерируем случайное количество лапок
            paw_count = random.randint(paw_min, paw_max)
            
            # Добавляем лапки к балансу
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = current_balance + paw_count
            
            cursor.execute(
                "UPDATE users SET last_spin_date = ?, balance = ? WHERE id = ?",
                (datetime.now().isoformat(), new_balance, user_id)
            )
            conn.commit()
            conn.close()
            
            return {"success": True, "gift": selected_gift, "paw_count": paw_count}
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
            
            return {"success": True, "gift": selected_gift}
    except Exception as e:
        print(f"Error in spin: {e}")
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
        
        conn = sqlite3.connect(DB_PATH)
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT inventory, balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        balance = result[1] or 0
        
        if request.index < 0 or request.index >= len(inventory):
            conn.close()
            return {"success": False, "message": "Invalid index"}
        
        if inventory[request.index] != request.giftName:
            conn.close()
            return {"success": False, "message": "Gift mismatch"}
        
        cursor.execute("SELECT price, gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        price_result = cursor.fetchone()
        
        if not price_result:
            conn.close()
            return {"success": False, "message": "Price not found"}
        
        price = price_result[0]
        gift_id = price_result[1] if len(price_result) > 1 else None
        
        inventory.pop(request.index)
        
        new_balance = balance + price
        
        cursor.execute(
            "UPDATE users SET inventory = ?, balance = ? WHERE id = ?",
            (json.dumps(inventory), new_balance, user_id)
        )
        conn.commit()
        conn.close()
        
        return {"success": True, "newBalance": new_balance, "price": price}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/get-balance")
async def get_balance(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "balance": 0, "bonusBalance": 0}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "balance": 0, "bonusBalance": 0}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance, bonus_balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        balance = result[0] if result and result[0] is not None else 0
        bonus_balance = result[1] if result and result[1] is not None else 0
        return {"valid": True, "balance": balance, "bonusBalance": bonus_balance}
    except Exception as e:
        return {"valid": False, "balance": 0, "bonusBalance": 0}

@router.post("/get-prices")
async def get_prices(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "prices": {}}
    
    try:
        conn = sqlite3.connect(DB_PATH)
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        
        # Проверяем индекс
        if request.index < 0 or request.index >= len(inventory):
            conn.close()
            return {"success": False, "message": "Invalid index"}
        
        # Проверяем совпадение подарка
        if inventory[request.index] != request.giftName:
            conn.close()
            return {"success": False, "message": "Gift mismatch"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Отправляем подарок через Pyrogram
        send_success, error_msg = await send_gift_async(user_id, gift_id, pyrogram_app)
        
        if not send_success:
            conn.close()
            return {
                "success": False, 
                "message": "Подарок не отправился из-за ошибки",
                "error": error_msg or "Неизвестная ошибка",
                "needsManual": True
            }
        
        # Удаляем подарок из инвентаря
        inventory.pop(request.index)
        
        cursor.execute(
            "UPDATE users SET inventory = ? WHERE id = ?",
            (json.dumps(inventory), user_id)
        )
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Подарок успешно отправлен!"}
    except Exception as e:
        print(f"Error in withdraw_gift: {e}")
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем инвентарь
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        
        # Проверяем индекс
        if request.index < 0 or request.index >= len(inventory):
            conn.close()
            return {"success": False, "message": "Invalid index"}
        
        # Проверяем совпадение подарка
        if inventory[request.index] != request.giftName:
            conn.close()
            return {"success": False, "message": "Gift mismatch"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря
        inventory.pop(request.index)
        
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
