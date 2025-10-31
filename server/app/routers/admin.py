from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
from app.config import BOT_TOKEN, ADMIN_IDS, DB_PATH
from app.utils import validate_init_data
from aiogram import Bot

router = APIRouter(prefix="/api", tags=["admin"])

class ValidateRequest(BaseModel):
    initData: str

class UpdateChanceRequest(BaseModel):
    initData: str
    giftName: str
    visibleChance: float
    realChance: float
    pawMin: int = 0
    pawMax: int = 0

class RefundPaymentRequest(BaseModel):
    initData: str
    userId: int
    transactionId: str
    deductFromBalance: bool = False

class UpdateCrashSettingsRequest(BaseModel):
    initData: str
    maxMultiplier: float

@router.post("/get-chances")
async def get_chances(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "chances": []}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "chances": []}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        if user_id not in ADMIN_IDS:
            return {"valid": False, "chances": []}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, visible_chance, real_chance, paw_min, paw_max FROM gift_chances")
        results = cursor.fetchall()
        conn.close()
        
        chances = [{"name": r[0], "visible": r[1], "real": r[2], "pawMin": r[3] or 0, "pawMax": r[4] or 0} for r in results]
        return {"valid": True, "chances": chances}
    except Exception:
        return {"valid": False, "chances": []}

@router.post("/update-chances")
async def update_chances(request: UpdateChanceRequest):
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        # Валидация pawMin и pawMax на сервере
        paw_min = max(0, min(100, request.pawMin))
        paw_max = max(0, min(100, request.pawMax))
        
        # Проверка что min <= max
        if paw_min > paw_max and paw_max > 0:
            paw_min, paw_max = paw_max, paw_min
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_chances SET visible_chance = ?, real_chance = ?, paw_min = ?, paw_max = ? WHERE gift_name = ?",
            (request.visibleChance, request.realChance, paw_min, paw_max, request.giftName)
        )
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in update_chances: {e}")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/admin/refund-payment")
async def refund_payment(request: RefundPaymentRequest):
    """Возврат платежа в Telegram Stars"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        admin_id = user.get('id')
        
        # Проверка прав администратора
        if admin_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        # Выполняем возврат через aiogram
        bot = Bot(token=BOT_TOKEN)
        
        try:
            # Получаем информацию о сумме транзакции перед возвратом
            transaction_amount = 0
            if request.deductFromBalance:
                try:
                    # Получаем историю транзакций пользователя
                    transactions = await bot.get_star_transactions(user_id=request.userId, limit=100)
                    
                    # Ищем нужную транзакцию по telegram_payment_charge_id
                    for transaction in transactions.transactions:
                        if hasattr(transaction, 'id') and transaction.id == request.transactionId:
                            transaction_amount = transaction.amount
                            print(f"Found transaction: {request.transactionId}, amount: {transaction_amount}")
                            break
                    
                    if transaction_amount == 0:
                        print(f"⚠️ Transaction {request.transactionId} not found in history, cannot determine amount")
                except Exception as e:
                    print(f"⚠️ Error getting transaction info: {e}")
            
            # Выполняем возврат
            result = await bot.refund_star_payment(
                user_id=request.userId,
                telegram_payment_charge_id=request.transactionId
            )
            
            await bot.session.close()
            
            if result:
                # Списываем с баланса если флаг установлен
                new_balance = None
                if request.deductFromBalance and transaction_amount > 0:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    # Вычитаем сумму транзакции из баланса пользователя
                    cursor.execute(
                        "UPDATE users SET balance = balance - ? WHERE id = ?",
                        (transaction_amount, request.userId)
                    )
                    
                    # Получаем новый баланс
                    cursor.execute("SELECT balance FROM users WHERE id = ?", (request.userId,))
                    balance_result = cursor.fetchone()
                    new_balance = balance_result[0] if balance_result else 0
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ Balance deducted: user_id={request.userId}, amount={transaction_amount}, new_balance={new_balance}")
                elif request.deductFromBalance and transaction_amount == 0:
                    print(f"⚠️ Cannot deduct balance - transaction amount unknown")
                
                print(f"✅ Refund successful: user_id={request.userId}, transaction_id={request.transactionId}, admin={admin_id}")
                
                response_data = {"success": True, "message": "Платеж возвращен"}
                if new_balance is not None:
                    response_data["newBalance"] = new_balance
                    response_data["deductedAmount"] = transaction_amount
                
                return response_data
            else:
                return {"success": False, "message": "Не удалось вернуть платеж"}
                
        except Exception as e:
            await bot.session.close()
            error_msg = str(e)
            print(f"❌ Refund failed: {error_msg}")
            return {"success": False, "message": f"Ошибка возврата: {error_msg}"}
            
    except Exception as e:
        print(f"Error in refund_payment: {e}")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/crash/get-settings")
async def get_crash_settings(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "maxMultiplier": 1000.0}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "maxMultiplier": 1000.0}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        if user_id not in ADMIN_IDS:
            return {"valid": False, "maxMultiplier": 1000.0}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT max_multiplier FROM crash_settings WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        max_mult = result[0] if result else 1000.0
        return {"valid": True, "maxMultiplier": max_mult}
    except Exception as e:
        print(f"Error in get_crash_settings: {e}")
        return {"valid": False, "maxMultiplier": 1000.0}

@router.post("/crash/update-settings")
async def update_crash_settings(request: UpdateCrashSettingsRequest):
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        if request.maxMultiplier < 2.0 or request.maxMultiplier > 100000.0:
            return {"success": False, "message": "Максимальный коэффициент должен быть от 2.0 до 100000.0"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE crash_settings SET max_multiplier = ? WHERE id = 1",
            (request.maxMultiplier,)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Crash max_multiplier updated to {request.maxMultiplier}x by admin {user_id}")
        return {"success": True}
    except Exception as e:
        print(f"Error in update_crash_settings: {e}")
        return {"success": False, "message": "Ошибка сервера"}
