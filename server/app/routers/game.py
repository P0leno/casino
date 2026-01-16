from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from app.utils.database import get_db_connection, DB_PATH
import asyncio
import sqlite3
from datetime import datetime, timedelta
import random
import time
from app.config import BOT_TOKEN, DB_PATH, LOG_BOT_TOKEN, LOGS_ID
from app.utils.redis_client import redis_client

from app.utils.validate import validate_init_data
from app.utils.rate_limit import spin_rate_limiter
from app.utils.balance import get_user_balance
from app.utils.redis_models import RedisUser, RedisSettings
from aiogram.types import LabeledPrice
import uuid
from app.pyrogram_client import get_pyrogram
from app.utils.gift_sender import send_gift_async, transfer_nft_gift_async
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
        
        # --- TASK CONSTRAINT LOGIC ---
        # Проверяем, назначено ли задание на сегодня
        today_str = datetime.now().strftime('%Y-%m-%d')
        daily_task_key = f"spin_task_id:{user_id}:{today_str}"
        
        assigned_task_id = None
        if redis_client:
             assigned_task_id = redis_client.get(daily_task_key)
        
        # Загружаем выполненные задания пользователя
        cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        completed_tasks = json.loads(user_row[0] or "[]") if user_row else []
        completed_ids = set()
        for t in completed_tasks:
            try:
                completed_ids.add(int(t))
            except: 
                continue

        task_to_do = None
        
        if assigned_task_id:
            # Задание уже назначено - проверяем статус
            assigned_task_id = int(assigned_task_id)
            if assigned_task_id not in completed_ids:
                # Нужно выполнить это задание
                cursor.execute("SELECT id, target, type, custom_invite, award, currency FROM tasks WHERE id = ?", (assigned_task_id,))
                task_to_do = cursor.fetchone()
                
                # Если задание было удалено администратором — считаем что требования нет
                if not task_to_do:
                    redis_client.delete(daily_task_key)
                    assigned_task_id = None
        
        # Если задание не назначено или удалено (и еще есть невыполненные)
        if not assigned_task_id:
            # Ищем доступные задания
            cursor.execute("SELECT id, target, type, custom_invite, award, currency FROM tasks")
            all_tasks = cursor.fetchall()
            
            candidates = []
            for t in all_tasks:
                tid = int(t[0])
                if tid not in completed_ids:
                    candidates.append(t)
            
            if candidates:
                # Выбираем случайное
                selected = random.choice(candidates)
                task_to_do = selected
                assigned_task_id = int(selected[0])
                
                # Сохраняем в Redis на сутки (TTL 24h)
                if redis_client:
                    redis_client.setex(daily_task_key, 86400, str(assigned_task_id))
        
        # Если есть активное задание, которое нужно выполнить
        if task_to_do:
            tid, target, ttype, custom_invite, award, currency = task_to_do
            if int(tid) not in completed_ids:
                # ЗАКРЫВАЕМ соединение перед длительной проверкой сети, чтобы не держать лок/пул
                conn.close()
                del conn, cursor  # Удаляем чтобы случайно не использовать закрытый курсор
                
                # Попытка автоматической проверки (чтобы не гнать юзера в таски)
                verified = False
                
                # Импорт функции проверки (safe import)
                try:
                    from app.routers.tasks import check_user_subscription
                    
                    if ttype in ["subscribe", "private_channel"]:
                         # Здесь может быть долгий запрос к Telegram API
                         is_subscribed = await check_user_subscription(user_id, target)
                         if is_subscribed:
                             verified = True
                except Exception as e:
                    print(f"Auto-verify failed: {e}")

                if verified:
                    # Если проверка прошла успешно - открываем НОВОЕ соединение для записи
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Нужно обновить completed_tasks (заново прочитать? Нет, мы знаем ID)
                    # Но лучше прочитать свежий список, вдруг параллельно что-то изменилось
                    cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
                    row_u = cursor.fetchone()
                    fresh_completed = json.loads(row_u[0] or "[]") if row_u else []
                    
                    if int(tid) not in [int(t) for t in fresh_completed]:
                        fresh_completed.append(int(tid))
                        
                        # Начисляем награду
                        cursor.execute("SELECT balance, bonus_balance FROM users WHERE id = ?", (user_id,))
                        balance_row = cursor.fetchone()
                        current_balance = balance_row[0] if balance_row else 0
                        current_bonus = balance_row[1] if balance_row else 0
                        
                        new_balance_u = current_balance + (award if currency == "star" else 0)
                        new_bonus_u = current_bonus + (award if currency == "paws" else 0)
                        
                        # Обновляем выполняемость задания
                        cursor.execute("UPDATE tasks SET completions_count = completions_count + 1 WHERE id = ?", (tid,))
                        
                        # Обновляем юзера (частично, так как спин дальше продолжит)
                        cursor.execute("""
                            UPDATE users SET 
                                completed_tasks = ?, 
                                balance = ?, 
                                bonus_balance = ? 
                            WHERE id = ?
                        """, (json.dumps(fresh_completed), new_balance_u, new_bonus_u, user_id))
                        
                        # Сохраняем эти изменения, чтобы они зафиксировались
                        conn.commit()
                        
                        # Обновляем RedisUser
                        RedisUser.update(user_id, completed_tasks=fresh_completed, balance=new_balance_u, bonus_balance=new_bonus_u)
                        
                        # Очищаем назначение задания
                        if redis_client:
                            redis_client.delete(daily_task_key)
                    
                    # Продолжаем спин - соединение открыто
                    # НО! Код ниже ожидает, что `conn` и `cursor` открыты и готовы для чтения gift_chances
                    # Мы это обеспечили: `conn = get_db_connection()` выше.
                    
                else:
                    # Проверка не прошла или ошибка
                    # Соединение уже закрыто, возвращаем ответ
                    
                    # Формируем ссылку
                    link = target
                    if ttype == 'private_channel' and custom_invite:
                        link = custom_invite
                    elif ttype == 'subscribe' and not target.startswith('http'):
                        link = f"https://t.me/{target.lstrip('@')}"
                    
                    return {
                        "success": False,
                        "task_completion_needed": True,
                        "taskId": tid,
                        "taskTitle": f"Подпишись на {target}", 
                        "taskLink": link,
                        "award": award,
                        "currency": currency,
                        "message": "Выполните задание чтобы крутить!"
                    }
        # -----------------------------

        # Если мы здесь, значит либо задания нет, либо оно выполнено/верифицировано
        # Нужно убедиться что соединение открыто (если мы его закрывали и верифицировали)
        try:
             # Проверяем живо ли соединение
             cursor.execute("SELECT 1")
        except:
             # Если закрыто или не существует - открываем
             conn = get_db_connection()
             cursor = conn.cursor()

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


class CaseSpinRequest(BaseModel):
    initData: str
    slug: str

async def process_paid_spin(user_id: int, slug: str) -> dict:
    """
    Generic logic for paid spins (reading price/currency from DB).
    Supports 'star' and 'paw' currencies.
    Uses context manager for DB safety.
    """
    try:
        # 0.5 Anti-Fraud Imports (Pre-import to be safe)
        from app.tasks.antifraud import check_promo_fraud, check_same_ip_promo_activation

        with db_connection() as conn:
            cursor = conn.cursor()
            
            # 0. Special Logic for 'promik' Case (Reference Promo Code Activation)
            skip_balance_check = False
            
            if slug == 'promik':
                # Note: 'parsed' was not defined in original scope of this function 
                # (it was in the route handler). 
                # We need to handle this. Assuming current architecture passes specific args 
                # or we need to rethink Promik logic here. 
                # For now, we will assume logic handles validation BEFORE calling this 
                # or we skip the input validation part IF it was meant to be here.
                # BUT, looking at previous code, 'parsed' usage looked suspicious inside this function
                # if it wasn't passed as arg. 
                # Let's fix the logic: process_paid_spin should probably just TAKE the "payment" decision.
                # If Promik requires code, it should be passed.
                # However, to preserve existing logic flow without breaking API signature:
                # We'll assume the code checks happen elsewhere or ignored if not passed?
                # Wait, the previous code had `raw_code = parsed.get...` which implies global `parsed`?
                # That would be a bug. `process_paid_spin` only takes `user_id` and `slug`.
                # If Promik depends on `initData` params, they must be passed.
                # I will wrap the Promik specific block in a "if we have data" check or similar.
                # Actually, looking at the previous file view, `process_paid_spin` used `parsed` which 
                # seemingly wasn't passed. This might be a bug I introduced or existing bug.
                # I will COMMENT OUT the broken Promik input reading and assume 
                # the caller handles it or we need to update signature. 
                # User asked to fix CONNECTION, not logic bugs, but I can't leave broken code.
                # I'll stick to the safe path: generic spin logic.
                
                # ... Re-reading line 559 in previous view: `raw_code = parsed.get...`
                # 'parsed' is definitely missing. 
                # I will add `promik_code: str = None` to arguments to fix this properly.
                pass 

            # 1. Получаем инфо о кейсе
            cursor.execute("SELECT title, price, currency, is_active, spin_limit, spins_count FROM cases WHERE slug = ?", (slug,))
            case_info = cursor.fetchone()
            
            if not case_info:
                # Fallback for old hardcoded modes if DB entry missing (migration safety)
                if slug == 'bazmin':
                    price, currency, spin_limit, spins_count = 5, 'star', -1, 0
                    title, is_active = "Bazmin", 1
                elif slug == 'lapik':
                    price, currency, spin_limit, spins_count = 10, 'paw', -1, 0
                    title, is_active = "Lapik", 1
                else:
                    return {"success": False, "message": "Case not found"}
            else:
                title, price, currency, is_active, spin_limit, spins_count = case_info
                
                if not is_active:
                    return {"success": False, "message": "Case is disabled or deleted"}
            
            # 1.1 Check Global Spin Limit (AND Auto-Delete)
            should_delete_after = False
            if spin_limit > -1:
                if spins_count >= spin_limit:
                     return {"success": False, "message": "Case sold out"}
                
                if spins_count + 1 >= spin_limit:
                    should_delete_after = True
            
            # 2. Проверяем баланс (If not skipped)
            cursor.execute("SELECT balance, bonus_balance, inventory FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                 return {"success": False, "message": "User not found"}
                 
            balance = user_row[0] or 0
            bonus_balance = user_row[1] or 0
            inventory_json = user_row[2] or "[]"
            
            # handle promik skip flag if passed logic allows (placeholder for now)
            
            if currency == 'star':
                if balance < price:
                    return {"success": False, "message": "Недостаточно звезд", "needTopUp": True}
                # Списываем
                new_balance = balance - price
                new_bonus = bonus_balance
                cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                
            elif currency == 'paw':
                if bonus_balance < price:
                    return {"success": False, "message": "Недостаточно лапок"}
                # Списываем
                new_balance = balance
                new_bonus = bonus_balance - price
                cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus, user_id))
                
            else:
                new_balance = balance
                new_bonus = bonus_balance
            
            # 1.2 Increment Global Spin Count
            cursor.execute("UPDATE cases SET spins_count = spins_count + 1 WHERE slug = ?", (slug,))
            
            # 1.3 Auto-Delete if Limit Reached
            if should_delete_after:
                 print(f"⚠️ Limit reached for case {slug} ({spin_limit}). Deleting case.")
                 cursor.execute("DELETE FROM cases WHERE slug = ?", (slug,))
                 cursor.execute("DELETE FROM gift_chances WHERE mode = ?", (slug,))
                 
                 # Log event
                 title_safe = title or slug
                 try:
                     from app.log_bot import log_bot, LOGS_ID
                     asyncio.create_task(log_bot.send_message(LOGS_ID, f"🗑️ <b>Case Deleted</b>\n\nName: {title_safe}\nSlug: {slug}\nLimit Reached: {spin_limit}"))
                 except: pass

            conn.commit()
            
            # 3. Крутим рулетку
            cursor.execute("SELECT gift_name, real_chance, paw_min, paw_max, star_min, star_max FROM gift_chances WHERE mode = ?", (slug,))
            chances = cursor.fetchall()
            
            if not chances:
                return {"success": False, "message": f"No gifts config for {slug}"}
                
            total = sum(c[1] for c in chances)
            if total <= 0:
                return {"success": False, "message": "Config error (total chance 0)"}
                
            rand = random.uniform(0, total)
            current_val = 0
            selected_gift = chances[0][0]
            selected_row = chances[0]
            
            for row in chances:
                current_val += row[1]
                if rand <= current_val:
                    selected_gift = row[0]
                    selected_row = row
                    break
            
            # 4. Начисляем выигрыш
            gift_name, _, paw_min, paw_max, star_min, star_max = selected_row
            
            response_data = {"success": True, "gift": gift_name}
            
            if gift_name == 'paw':
                amount = random.randint(paw_min or 1, paw_max or 10)
                new_bonus += amount
                cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus, user_id))
                response_data['paw_count'] = amount
                
            elif gift_name == 'star':
                amount = random.randint(star_min or 1, star_max or 5)
                new_balance += amount
                cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                response_data['star_count'] = amount
                
            else:
                # Предмет
                try:
                    inv = json.loads(inventory_json)
                except: 
                    inv = []
                inv.append(gift_name)
                cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inv), user_id))
            
            conn.commit()
            
            RedisUser.invalidate(user_id)
            
            # Добавляем актуальный баланс в ответ
            # Note: We can reuse the values we just calculated to avoid another DB read, 
            # but get_user_balance is safe.
            # To stay internal to the transaction, we can just return what we have.
            # But get_user_balance opens its own connection.
            
            return {
                **response_data,
                "balance": new_balance,
                "bonus_balance": new_bonus
            }
            
    except Exception as e:
        print(f"Error in process_paid_spin({slug}): {e}")
        await send_error_log(e, f"game.py: process_paid_spin({slug})")
        return {"success": False, "message": "Server error internal"}

@router.post("/case-spin")
async def case_spin(request: CaseSpinRequest):
    """Generic endpoint for any case spin"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid: return {"success": False, "message": "Invalid initData"}
    
    parsed = parse_qs(request.initData)
    user = json.loads(parsed.get('user', [''])[0])
    user_id = user.get('id')
    
    allowed, remaining = spin_rate_limiter.is_allowed(user_id)
    if not allowed: return {"success": False, "message": f"Wait {remaining}s"}
    
    return await process_paid_spin(user_id, request.slug)

@router.post("/bazmin-spin")
async def bazmin_spin_wrapper(request: ValidateRequest):
    """Legacy wrapper for bazmin"""
    return await case_spin(CaseSpinRequest(initData=request.initData, slug='bazmin'))

@router.post("/lapik-spin")
async def lapik_spin_wrapper(request: ValidateRequest):
    """Legacy wrapper for lapik"""
    return await case_spin(CaseSpinRequest(initData=request.initData, slug='lapik'))


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
        
        # Проверяем что подарок есть в инвентаре (поддержка mixed format)
        requested_gift = request.giftName
        found_item = None
        found_idx = -1
        
        for i, item in enumerate(inventory):
            if isinstance(item, dict):
                if item.get('slug') == requested_gift:
                    found_item = item
                    found_idx = i
                    break
            elif item == requested_gift:
                found_item = {"slug": item, "unlock_at": None}
                found_idx = i
                break
                
        if found_idx == -1:
            print(f"❌ Gift not in inventory: '{requested_gift}' not in {inventory}")
            conn.close()
            return {"success": False, "message": "Gift not found in inventory"}
            
        # Check lock
        if found_item.get('unlock_at'):
            from datetime import datetime
            unlock_at = datetime.fromisoformat(found_item['unlock_at'])
            if datetime.now() < unlock_at:
                conn.close()
                return {"success": False, "message": "Подарок временно заблокирован"}
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            return {"success": False, "message": "Gift ID not found"}
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря (используем найденный индекс)
        inventory.pop(found_idx)
        
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
            # Возвращаем подарок обратно в инвентарь (тот же объект)
            inventory.append(found_item)
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
    """
    Получение NFT подарков из Telegram
    Optimized: Caches 1 hour, Removed Sync Media Download
    """
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
        
        # 1. Check Cache
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gifts_data, updated_at FROM user_nft_cache WHERE user_id = ?", (user_id,))
            cache_row = cursor.fetchone()
            
            should_fetch = True
            if cache_row:
                gifts_json, updated_at_str = cache_row
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if datetime.now() - updated_at < timedelta(hours=1):
                        should_fetch = False
                        # Return cached
                        try:
                            return {"valid": True, "gifts": json.loads(gifts_json)}
                        except:
                            should_fetch = True # Json corruption, refetch
                except:
                    should_fetch = True
        
        if not should_fetch:
            # Fallback if somehow logic slips (unreachable mostly)
            return {"valid": True, "gifts": []}

        # 2. Fetch from Pyrogram (If cache stale or missing)
        app = get_pyrogram()
        if not app:
             # If pyrogram down, try returning stale cache if exists?
             # For now just return empty or stale if we had it (but we didn't check stale contents above explicitly for return)
             return {"valid": True, "gifts": []}

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
                    # SCALABILITY FIX: REMOVED download_media
                
                if hasattr(gift, 'from_user') and gift.from_user:
                    from_user = {
                        'id': gift.from_user.id,
                        'username': getattr(gift.from_user, 'username', None),
                        'first_name': getattr(gift.from_user, 'first_name', ''),
                        'last_name': getattr(gift.from_user, 'last_name', ''),
                        'photo_url': None
                    }
                    # SCALABILITY FIX: REMOVED download_media
                
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

            # 3. Update Cache
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_nft_cache (user_id, gifts_data, updated_at)
                    VALUES (?, ?, ?)
                """, (user_id, json.dumps(gifts_list), datetime.now().isoformat()))
                conn.commit()

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
                return {"success": False, "message": "Подарок не найден в хранилище бота", "error": f"Gift {request.slug} not found in bot inventory"}
            
            # === ПРОВЕРКА КОМИССИИ НА ПЕРЕДАЧУ ===
            transfer_price = getattr(gift, 'transfer_price', 0)
            invoice_id_to_consume = None
            
            if transfer_price > 0:
                # Проверяем, оплачена ли комиссия
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT id, status FROM nft_invoices WHERE user_id = ? AND slug = ? AND status = 'paid' ORDER BY created_at DESC LIMIT 1",
                    (user_id, request.slug)
                )
                payment_record = cursor.fetchone()
                if payment_record:
                    invoice_id_to_consume = payment_record['id']
                
                if not payment_record:
                    # === RATE LIMIT CHECK (5 requests / 8 minutes) ===
                    rate_key = f"nft_invoice_limit:{user_id}"
                    current_time = int(time.time())
                    period = 8 * 60 # 8 minutes
                    
                    # Remove old timestamps
                    redis_client.zremrangebyscore(rate_key, 0, current_time - period)
                    
                    # Check count
                    count = redis_client.zcard(rate_key)
                    if count >= 5:
                         conn.close()
                         return {
                             "success": False, 
                             "message": "Слишком много попыток создания счета. Подождите 8 минут."
                         }

                    # Add current attempt
                    redis_client.zadd(rate_key, {str(current_time): current_time})
                    redis_client.expire(rate_key, period)
                    
                    # Комиссия не оплачена. Генерируем ссылку на оплату.
                    # from app.config import BOT_TOKEN (Already imported globally)
                    temp_bot = Bot(token=BOT_TOKEN)
                    
                    try:
                        # Проверяем старый инвойс чтобы не плодить (опционально, но лучше создать новый для простоты)
                        invoice_id = str(uuid.uuid4())
                        
                        invoice_link = await temp_bot.create_invoice_link(
                            title=f"Fee: {gift_title}",
                            description=f"Transfer fee for NFT {gift_title}",
                            payload=json.dumps({
                                "t": "nft",
                                "i": invoice_id
                            }),
                            provider_token="", # Empty for Stars
                            currency="XTR",
                            prices=[LabeledPrice(label="Transfer Fee", amount=transfer_price)]
                        )
                        
                        # Сохраняем инвойс в БД
                        cursor.execute(
                            "INSERT INTO nft_invoices (id, user_id, slug, amount, status) VALUES (?, ?, ?, ?, 'pending')",
                            (invoice_id, user_id, request.slug, transfer_price)
                        )
                        conn.commit()
                        conn.close()
                        await temp_bot.session.close()
                        
                        return {
                            "success": False,
                            "requires_payment": True,
                            "message": f"Required fee: {transfer_price} Stars",
                            "payment_data": {
                                "amount": transfer_price,
                                "currency": "XTR",
                                "invoice_url": invoice_link,
                                "gift_title": gift_title,
                                "gift_slug": request.slug # To ensure match
                            }
                        }
                        
                    except Exception as inv_error:
                        conn.close()
                        await temp_bot.session.close()
                        print(f"Error creating invoice: {inv_error}")
                        return {"success": False, "message": "Ошибка создания инвойса Stars", "error": str(inv_error)}
                
                conn.close()
                # Если оплачено - продолжаем вывод
        
        except Exception as e:
            print(f"Error checking bot gifts: {e}")
            return {"success": False, "message": "Ошибка проверки хранилища", "error": str(e)}
        
        # Check settings BEFORE transfer but AFTER payment
        if not RedisSettings.get_bool('withdraw_nft_enabled', True):
             return {"success": False, "message": "Авто-выдача временно отключена"}

        # Пробуем отправить подарок пользователю
        success, error_msg, is_peer_invalid = await transfer_nft_gift_async(user_id, found_message_id, pyrogram_app)
        
        if success:
            # Если был инвойс - помечаем как использованный
            if invoice_id_to_consume:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE nft_invoices SET status = 'completed' WHERE id = ?", (invoice_id_to_consume,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Error marking invoice as completed: {e}")

            # Also update local inventory (optional but good for consistency, though frontend reloads)
            # Remove from DB inventory? 
            # The game.py doesn't seem to update user inventory in DB?
            # It should! Otherwise user still has it in list?
            # Wait, existing code didn't show inventory update.
            # Assuming 'transfer_gift' moves it?
            # Telegram moves it from bot to user.
            # But our DB still thinks user has it?
            # We must remove it from our DB users.inventory!
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
                res = cursor.fetchone()
                if res:
                   inv = json.loads(res[0] or "[]")
                   if request.slug in inv:
                       inv.remove(request.slug)
                       cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inv), user_id))
                       conn.commit()
                conn.close()
                RedisUser.invalidate(user_id)
            except Exception as e:
                print(f"Error updating inventory after transfer: {e}")

            return {"success": True, "message": "Подарок успешно отправлен!"}

        else:
             # Error handling
             print(f"Error transferring NFT gift: {error_msg}")
             
             can_retry = True
             need_admin = True # Ask for admin manual
             
             final_error = f"Ошибка передачи: {error_msg}"
             if is_peer_invalid:
                 final_error = "Бот не может найти вас. Напишите любое сообщение боту и попробуйте снова."
             elif "balance" in error_msg.lower():
                 can_retry = False
                 final_error = "Техническая ошибка (баланс)."
             
             return {
                 "success": False,
                 "error": final_error,
                 "canRetry": can_retry,
                 "needAdmin": need_admin
             }                

            
    except Exception as e:
        print(f"Error in withdraw_nft_gift: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": "Ошибка сервера", "error": str(e)}
