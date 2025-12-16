from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from app.utils.database import get_db_connection, DB_PATH
import asyncio
from app.config import BOT_TOKEN, DB_PATH
from app.utils.redis_models import RedisSettings
from app.utils.validate import validate_init_data
from aiogram import Bot
from app.crash_game import crash_game

router = APIRouter(prefix="/api", tags=["admin"])

class ValidateRequest(BaseModel):
    initData: str

class GetChancesRequest(BaseModel):
    initData: str
    mode: str = 'free_spin'  # free_spin, bazmin, lapik, nistart, promik

class UpdateChanceRequest(BaseModel):
    initData: str
    giftName: str
    visibleChance: float
    realChance: float
    mode: str = 'free_spin'  # free_spin, bazmin, lapik, nistart, promik
    pawMin: int = 0
    pawMax: int = 0
    starMin: int = 1
    starMax: int = 5

class UpdatePaidChanceRequest(BaseModel):
    initData: str
    giftName: str
    visibleChance: float
    realChance: float
    pawMin: int = 0
    pawMax: int = 0
    starMin: int = 1
    starMax: int = 5

class RefundPaymentRequest(BaseModel):
    initData: str
    userId: int
    transactionId: str
    deductFromBalance: bool = False

class UpdateCrashSettingsRequest(BaseModel):
    initData: str
    maxMultiplier: float
    alwaysProfit: bool = False
    maxDebt: int = 300
    bigBetThreshold: int = 100
    bigBetLoseChance: int = 30

class UpdateSettingRequest(BaseModel):
    initData: str
    key: str
    value: str

@router.post("/get-chances")
async def get_chances(request: GetChancesRequest):
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
        
        if not RedisSettings.is_admin(user_id):
            return {"valid": False, "chances": []}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, visible_chance, real_chance, paw_min, paw_max, star_min, star_max FROM gift_chances WHERE mode = ?", (request.mode,))
        results = cursor.fetchall()
        conn.close()
        
        chances = [{"name": r[0], "visible": r[1], "real": r[2], "pawMin": r[3] or 0, "pawMax": r[4] or 0, "starMin": r[5] or 1, "starMax": r[6] or 5} for r in results]
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
        
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Not authorized"}
        
        # Валидация pawMin и pawMax на сервере
        paw_min = max(0, min(100, request.pawMin))
        paw_max = max(0, min(100, request.pawMax))
        
        # Проверка что min <= max
        if paw_min > paw_max and paw_max > 0:
            paw_min, paw_max = paw_max, paw_min
        
        # Валидация starMin и starMax
        star_min = max(1, min(100, request.starMin))
        star_max = max(1, min(100, request.starMax))
        
        if star_min > star_max:
            star_min, star_max = star_max, star_min
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_chances SET visible_chance = ?, real_chance = ?, paw_min = ?, paw_max = ?, star_min = ?, star_max = ? WHERE gift_name = ? AND mode = ?",
            (request.visibleChance, request.realChance, paw_min, paw_max, star_min, star_max, request.giftName, request.mode)
        )
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in update_chances: {e}")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/get-paid-chances")
async def get_paid_chances(request: ValidateRequest):
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
        
        if not RedisSettings.is_admin(user_id):
            return {"valid": False, "chances": []}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, visible_chance, real_chance, paw_min, paw_max, star_min, star_max FROM gift_chances WHERE mode = 'bazmin'")
        results = cursor.fetchall()
        conn.close()
        
        chances = [{"name": r[0], "visible": r[1], "real": r[2], "pawMin": r[3] or 0, "pawMax": r[4] or 0, "starMin": r[5] or 1, "starMax": r[6] or 5} for r in results]
        return {"valid": True, "chances": chances}
    except Exception:
        return {"valid": False, "chances": []}

@router.post("/update-paid-chances")
async def update_paid_chances(request: UpdatePaidChanceRequest):
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
        
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Not authorized"}
        
        # Валидация pawMin и pawMax на сервере
        paw_min = max(0, min(100, request.pawMin))
        paw_max = max(0, min(100, request.pawMax))
        
        # Проверка что min <= max
        if paw_min > paw_max and paw_max > 0:
            paw_min, paw_max = paw_max, paw_min
        
        # Валидация starMin и starMax
        star_min = max(1, min(100, request.starMin))
        star_max = max(1, min(100, request.starMax))
        
        if star_min > star_max:
            star_min, star_max = star_max, star_min
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_chances SET visible_chance = ?, real_chance = ?, paw_min = ?, paw_max = ?, star_min = ?, star_max = ? WHERE gift_name = ? AND mode = 'bazmin'",
            (request.visibleChance, request.realChance, paw_min, paw_max, star_min, star_max, request.giftName)
        )
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in update_paid_chances: {e}")
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
        if not RedisSettings.is_admin(admin_id):
            return {"success": False, "message": "Not authorized"}
        
        # Выполняем возврат через aiogram
        bot = Bot(token=BOT_TOKEN)
        
        try:
            # Получаем информацию о сумме транзакции перед возвратом
            transaction_amount = 0
            if request.deductFromBalance:
                try:
                    # Получаем историю транзакций бота
                    transactions = await bot.get_star_transactions(limit=100)
                    
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
                    conn = get_db_connection()
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
        
        if not RedisSettings.is_admin(user_id):
            return {"valid": False, "maxMultiplier": 1000.0}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'max_crash_multiplier'")
        result = cursor.fetchone()
        max_mult = float(result[0]) if result else 10.0
        
        cursor.execute("SELECT value FROM settings WHERE key = 'crash_always_profit'")
        always_profit_result = cursor.fetchone()
        always_profit = always_profit_result[0] == '1' if always_profit_result else False
        
        cursor.execute("SELECT value FROM settings WHERE key = 'crash_max_debt'")
        max_debt_result = cursor.fetchone()
        max_debt = int(max_debt_result[0]) if max_debt_result else 300
        
        cursor.execute("SELECT value FROM settings WHERE key = 'crash_big_bet_threshold'")
        big_bet_threshold_result = cursor.fetchone()
        big_bet_threshold = int(big_bet_threshold_result[0]) if big_bet_threshold_result else 100
        
        cursor.execute("SELECT value FROM settings WHERE key = 'crash_big_bet_lose_chance'")
        big_bet_lose_chance_result = cursor.fetchone()
        big_bet_lose_chance = int(big_bet_lose_chance_result[0]) if big_bet_lose_chance_result else 30
        conn.close()
        
        return {
            "valid": True, 
            "maxMultiplier": max_mult, 
            "alwaysProfit": always_profit, 
            "maxDebt": max_debt,
            "bigBetThreshold": big_bet_threshold,
            "bigBetLoseChance": big_bet_lose_chance
        }
    except Exception as e:
        print(f"Error in get_crash_settings: {e}")
        return {"valid": False, "maxMultiplier": 10.0, "alwaysProfit": False, "maxDebt": 300, "bigBetThreshold": 100, "bigBetLoseChance": 30}

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
        
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Not authorized"}
        
        if request.maxMultiplier < 2.0 or request.maxMultiplier > 100000.0:
            return {"success": False, "message": "Максимальный коэффициент должен быть от 2.0 до 100000.0"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'max_crash_multiplier'",
            (str(request.maxMultiplier),)
        )
        
        # Обновляем crash_always_profit
        always_profit_value = '1' if request.alwaysProfit else '0'
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES ('crash_always_profit', ?, 'Режим всегда в плюсе (0/1)', CURRENT_TIMESTAMP)",
            (always_profit_value,)
        )
        
        # Обновляем crash_max_debt
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES ('crash_max_debt', ?, 'Порог долга для агрессивного режима', CURRENT_TIMESTAMP)",
            (str(request.maxDebt),)
        )
        
        # Обновляем crash_big_bet_threshold
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES ('crash_big_bet_threshold', ?, 'Порог большой ставки', CURRENT_TIMESTAMP)",
            (str(request.bigBetThreshold),)
        )
        
        # Обновляем crash_big_bet_lose_chance
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES ('crash_big_bet_lose_chance', ?, 'Шанс проигрыша на большой ставке (%)', CURRENT_TIMESTAMP)",
            (str(request.bigBetLoseChance),)
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Crash settings updated: max_mult={request.maxMultiplier}x, always_profit={request.alwaysProfit}, max_debt={request.maxDebt}, big_bet_threshold={request.bigBetThreshold}, big_bet_lose_chance={request.bigBetLoseChance}%")
        return {"success": True}
    except Exception as e:
        print(f"Error in update_crash_settings: {e}")
        return {"success": False, "message": "Ошибка сервера"}



class ExplodeRequest(BaseModel):
    initData: str

@router.post("/admin/crash/explode")
async def explode_crash(request: ExplodeRequest):
    """Принудительно взорвать ракету (только для админов)"""
    try:
        is_valid = validate_init_data(request.initData, BOT_TOKEN)
        if not is_valid:
            return {"success": False, "message": "Invalid init data"}
        
        parsed = parse_qs(request.initData)
        user_data = json.loads(parsed['user'][0])
        user_id = int(user_data['id'])
        
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Forbidden"}
        
        if not crash_game.is_running:
            return {"success": False, "message": "Игра не запущена"}
        
        # Останавливаем игру и завершаем раунд
        await crash_game.end_round()
        
        return {"success": True, "message": "Ракета взорвана"}
    except Exception as e:
        print(f"Error exploding crash: {e}")
        return {"success": False, "message": str(e)}

@router.post("/get-settings")
async def get_settings(request: ValidateRequest):
    """Получение всех настроек (только для админов)"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "settings": {}}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "settings": {}}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Проверяем что пользователь админ
        if not RedisSettings.is_admin(user_id):
            return {"valid": False, "settings": {}, "error": "Not admin"}
        
        # Читаем из Redis (с fallback на SQLite)
        settings = RedisSettings.get_all()
        
        # Извлекаем maintenance_mode для удобства
        maintenance_mode = settings.get('maintenance_mode', {}).get('value', '0') == '1'
        
        return {
            "valid": True, 
            "settings": settings,
            "maintenanceMode": maintenance_mode
        }
    except Exception as e:
        print(f"Error getting settings: {e}")
        return {"valid": False, "settings": {}, "error": str(e)}

@router.post("/get-maintenance")
async def get_maintenance(request: ValidateRequest):
    """Получить статус режима технических работ (для админов)"""
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
        
        # Проверка прав админа
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Access denied"}
        
        # Получаем статус
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        result = cursor.fetchone()
        conn.close()
        
        enabled = result[0] == '1' if result else False
        
        return {
            "success": True,
            "maintenance_mode": enabled
        }
        
    except Exception as e:
        print(f"Error getting maintenance mode: {e}")
        return {"success": False, "message": "Server error"}

@router.post("/toggle-maintenance")
async def toggle_maintenance(request: ValidateRequest):
    """Переключить режим технических работ (только для админов)"""
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
        
        # Проверка прав админа
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Access denied"}
        
        # Получаем текущее значение
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        result = cursor.fetchone()
        
        current = result[0] if result else '0'
        new_value = '0' if current == '1' else '1'
        
        # Обновляем
        cursor.execute(
            "UPDATE settings SET value = ? WHERE key = 'maintenance_mode'",
            (new_value,)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Maintenance mode toggled by admin {user_id}: {current} -> {new_value}")
        
        return {
            "success": True,
            "maintenance_mode": new_value == '1'
        }
        
    except Exception as e:
        print(f"Error toggling maintenance mode: {e}")
        return {"success": False, "message": "Server error"}

@router.post("/update-setting")
async def update_setting(request: UpdateSettingRequest):
    """Обновление настройки (только для админов)"""
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
        
        # Проверяем что пользователь админ
        if not RedisSettings.is_admin(user_id):
            return {"success": False, "message": "Access denied"}
        
        # Серверная валидация значения
        sanitized_value = request.value
        
        # Для числовых настроек - только цифры и точка
        if request.key in ['shop_commission', 'sell_commission', 'max_crash_multiplier', 'ton_price_usd', 'custom_promo_refs_required']:
            import re
            # Удаляем всё кроме цифр и точки
            sanitized_value = re.sub(r'[^0-9.]', '', request.value)
            
            # Для custom_promo_refs_required - только целые числа
            if request.key == 'custom_promo_refs_required':
                sanitized_value = re.sub(r'[^0-9]', '', request.value)
                try:
                    int_val = int(sanitized_value)
                    if int_val < 1 or int_val > 1000:
                        return {"success": False, "message": "Значение должно быть от 1 до 1000"}
                    sanitized_value = str(int_val)
                except ValueError:
                    return {"success": False, "message": "Некорректное числовое значение"}
        
        # Обновляем через Redis (автоматически обновит БД и Redis)
        success = RedisSettings.set(request.key, sanitized_value)
        
        if not success:
            return {"success": False, "message": "Setting not found"}
        
        # Если изменили комиссию магазина - запускаем пересчет цен
        if request.key == 'shop_commission':
            import asyncio
            from app.tasks.ton_price_updater import recalculate_gift_prices
            asyncio.create_task(recalculate_gift_prices())
            print(f"🔄 Запущен пересчет цен с новой комиссией: {request.value}%")
        
        return {"success": True, "message": f"Настройка {request.key} обновлена"}
    except Exception as e:
        print(f"Error updating setting: {e}")
        return {"success": False, "message": str(e)}

@router.post("/restart-server")
async def restart_server(request: ValidateRequest):
    """
    Перезапустить сервер с graceful shutdown
    Ждет завершения текущего краш раунда, закрывает WebSocket, затем перезапускает Python процесс
    """
    try:
        # Проверяем что это админ
        is_valid = validate_init_data(request.initData, BOT_TOKEN)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
        
        if not RedisSettings.is_admin(user_id):
            raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
        
        # Запускаем перезапуск в фоне
        from app.restart_monitor import handle_restart_command
        from app.log_bot import log_bot
        
        # Используем постоянный log_bot
        asyncio.create_task(handle_restart_command(None, log_bot))
        
        return {
            "success": True, 
            "message": "Перезапуск запущен. Сервер дождется завершения краш-раунда и перезагрузится."
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error restarting server: {e}")
        return {"success": False, "message": str(e)}
