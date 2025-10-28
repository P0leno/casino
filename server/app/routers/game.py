from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
import random
from app.config import BOT_TOKEN, DB_PATH
from app.utils import validate_init_data

router = APIRouter(prefix="/api", tags=["game"])

class ValidateRequest(BaseModel):
    initData: str

class SellGiftRequest(BaseModel):
    initData: str
    giftName: str
    index: int

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
        
        cursor.execute("SELECT price FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        price_result = cursor.fetchone()
        
        if not price_result:
            conn.close()
            return {"success": False, "message": "Price not found"}
        
        price = price_result[0]
        
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
