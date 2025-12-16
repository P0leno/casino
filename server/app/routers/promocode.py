from fastapi import APIRouter, Request
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from app.utils.database import get_db_connection, DB_PATH
import secrets
import string
from datetime import datetime
from app.config import BOT_TOKEN, DB_PATH
from app.utils.validate import validate_init_data
from app.utils.rate_limit import promo_mycode_rate_limiter
from app.utils.balance import get_user_balance

router = APIRouter(prefix="/api/promocode", tags=["promocode"])

class ActivateRequest(BaseModel):
    initData: str
    promoCode: str

class GenerateRequest(BaseModel):
    initData: str
    type: str = "ref"

class RenameRequest(BaseModel):
    initData: str
    newName: str

def verify_init_data(init_data: str):
    """
    Проверяет initData и возвращает user_data
    Возвращает None если невалидно
    """
    if not validate_init_data(init_data, BOT_TOKEN):
        return None
    
    try:
        parsed = parse_qs(init_data)
        user_data_str = parsed.get('user', [''])[0]
        
        if not user_data_str:
            return None
        
        user_data = json.loads(user_data_str)
        return user_data
    except:
        return None

def generate_promo_code(length=8):
    """Генерирует случайный промокод из букв и цифр"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def sanitize_promo_name(name):
    """Санитизация названия промокода - защита от XSS и SQL"""
    # Удаляем все кроме букв, цифр, дефиса и подчеркивания
    import re
    sanitized = re.sub(r'[^A-Z0-9_-]', '', name.upper())
    return sanitized[:16]  # Максимум 16 символов

@router.post("/activate")
async def activate_promocode(activate_req: ActivateRequest, request: Request):
    """Активация промокода пользователем"""
    user_data = verify_init_data(activate_req.initData)
    if not user_data:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = user_data['id']
    promo_code = sanitize_promo_name(activate_req.promoCode)
    
    # Получаем IP для антифрод проверки
    client_ip = request.client.host if request.client else "unknown"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Проверяем существование промокода
        cursor.execute(
            "SELECT id, owner, reward, type FROM promocodes WHERE promo = ?",
            (promo_code,)
        )
        promo = cursor.fetchone()
        
        if not promo:
            return {"success": False, "error": "Промокод не найден"}
        
        promo_id, owner_id, reward, promo_type = promo
        
        # Проверяем, что пользователь не активирует свой собственный промокод
        if owner_id == user_id:
            return {"success": False, "error": "Нельзя активировать свой промокод"}
        
        # АНТИФРОД: проверяем совпадение IP с владельцем промокода
        from app.tasks.antifraud import check_promo_fraud, check_same_ip_promo_activation
        import asyncio
        
        # Проверка 1: активатор и владелец с одного IP
        is_fraud = await check_promo_fraud(user_id, client_ip, owner_id)
        if is_fraud:
            conn.close()
            return {"success": False, "error": "Подозрительная активность. Вы заблокированы."}
        
        # Проверка 2: два активатора одного промокода с одного IP
        is_same_ip_fraud = await check_same_ip_promo_activation(user_id, client_ip, promo_id)
        if is_same_ip_fraud:
            conn.close()
            return {"success": False, "error": "Подозрительная активность. Вы заблокированы."}
        
        # Получаем список активированных промокодов пользователя (храним ID промокодов)
        cursor.execute(
            "SELECT activated_promocodes FROM users WHERE id = ?",
            (user_id,)
        )
        user_result = cursor.fetchone()
        
        if not user_result:
            return {"success": False, "error": "Пользователь не найден"}
        
        activated_promocodes = json.loads(user_result[0] or '[]')
        
        # Проверяем, не активирован ли уже этот промокод (по ID)
        if promo_id in activated_promocodes:
            return {"success": False, "error": "Промокод уже активирован"}
        
        # Если это реферальный промокод (ref или refCustom), проверяем что юзер еще не активировал никакой реф промокод
        if promo_type in ['ref', 'refCustom']:
            # Получаем все активированные промокоды юзера и проверяем их типы
            if activated_promocodes:
                cursor.execute(
                    f"SELECT type FROM promocodes WHERE id IN ({','.join('?' * len(activated_promocodes))})",
                    activated_promocodes
                )
                activated_types = [row[0] for row in cursor.fetchall()]
                if 'ref' in activated_types or 'refCustom' in activated_types:
                    return {"success": False, "error": "Вы уже активировали реферальный промокод"}
        
        # Добавляем награду пользователю
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (reward, user_id)
        )
        
        # Добавляем ID промокода в список активированных
        activated_promocodes.append(promo_id)
        cursor.execute(
            "UPDATE users SET activated_promocodes = ? WHERE id = ?",
            (json.dumps(activated_promocodes), user_id)
        )
        
        # Увеличиваем счетчик приглашенных у владельца промокода
        cursor.execute(
            "UPDATE promocodes SET invited_count = invited_count + 1 WHERE id = ?",
            (promo_id,)
        )
        
        # Логируем активацию в promo_history
        cursor.execute(
            "INSERT INTO promo_history (promo_id, user_id, action_type) VALUES (?, ?, 'activated')",
            (promo_id, user_id)
        )
        
        conn.commit()
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        
        return {
            "success": True,
            "reward": reward,
            "message": f"Промокод активирован! Получено {reward} звезд",
            **user_balance
        }
        
    except Exception as e:
        conn.rollback()
        print(f"Error activating promocode: {e}")
        return {"success": False, "error": "Ошибка активации промокода"}
    finally:
        conn.close()

@router.post("/generate")
async def generate_promocode(request: GenerateRequest):
    """Генерация промокода для пользователя"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = user_data['id']
    promo_type = request.type
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем настройку минимума рефералов
        cursor.execute("SELECT value FROM settings WHERE key = 'custom_promo_refs_required'")
        setting = cursor.fetchone()
        required_refs = int(setting[0]) if setting else 10
        
        # Проверяем, есть ли уже промокод у пользователя (ref или refCustom)
        cursor.execute(
            "SELECT promo, invited_count, type FROM promocodes WHERE owner = ? AND (type = 'ref' OR type = 'refCustom')",
            (user_id,)
        )
        existing_promo = cursor.fetchone()
        
        if existing_promo:
            return {
                "success": True,
                "promoCode": existing_promo[0],
                "invitedCount": existing_promo[1],
                "promoType": existing_promo[2],
                "requiredRefs": required_refs,
                "message": "Промокод уже существует"
            }
        
        # Генерируем уникальный промокод (8 символов)
        max_attempts = 10
        promo_code = None
        
        for _ in range(max_attempts):
            temp_code = generate_promo_code(8)
            
            # Проверяем уникальность
            cursor.execute(
                "SELECT id FROM promocodes WHERE promo = ?",
                (temp_code,)
            )
            
            if not cursor.fetchone():
                promo_code = temp_code
                break
        
        if not promo_code:
            return {"success": False, "error": "Не удалось сгенерировать уникальный промокод"}
        
        # Сохраняем промокод в базу
        cursor.execute(
            """INSERT INTO promocodes (promo, type, xp, owner, reward) 
               VALUES (?, ?, ?, ?, ?)""",
            (promo_code, promo_type, 0, user_id, 25)
        )
        
        conn.commit()
        
        return {
            "success": True,
            "promoCode": promo_code,
            "invitedCount": 0,
            "promoType": promo_type,
            "requiredRefs": required_refs,
            "message": "Промокод успешно создан"
        }
        
    except Exception as e:
        conn.rollback()
        print(f"Error generating promocode: {e}")
        return {"success": False, "error": "Ошибка создания промокода"}
    finally:
        conn.close()

@router.post("/my-code")
async def get_my_promocode(request: GenerateRequest):
    """Получить существующий промокод пользователя"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = user_data['id']
    
    # Rate limit: 1 запрос в 15 секунд
    allowed, remaining_time = promo_mycode_rate_limiter.is_allowed(user_id)
    if not allowed:
        return {"success": False, "error": f"Попробуйте через {remaining_time}с"}
    
    promo_type = request.type
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем настройку минимума рефералов
        cursor.execute("SELECT value FROM settings WHERE key = 'custom_promo_refs_required'")
        setting = cursor.fetchone()
        required_refs = int(setting[0]) if setting else 10
        
        cursor.execute(
            "SELECT promo, invited_count, type FROM promocodes WHERE owner = ? AND (type = 'ref' OR type = 'refCustom')",
            (user_id,)
        )
        promo = cursor.fetchone()
        
        if promo:
            # Получаем refbalance пользователя
            cursor.execute("SELECT refbalance FROM users WHERE id = ?", (user_id,))
            refbalance_result = cursor.fetchone()
            refbalance = refbalance_result[0] if refbalance_result else 0
            
            return {
                "success": True,
                "promoCode": promo[0],
                "invitedCount": promo[1],
                "promoType": promo[2],
                "requiredRefs": required_refs,
                "refBalance": refbalance
            }
        else:
            return {
                "success": False,
                "error": "Промокод не найден"
            }
    except Exception as e:
        print(f"Error getting promocode: {e}")
        return {"success": False, "error": "Ошибка получения промокода"}
    finally:
        conn.close()

@router.post("/history")
async def get_promo_history(request: GenerateRequest):
    """Получить историю промокода (активации и пополнения)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = user_data['id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем промокод пользователя
        cursor.execute(
            "SELECT id FROM promocodes WHERE owner = ? AND (type = 'ref' OR type = 'refCustom')",
            (user_id,)
        )
        promo = cursor.fetchone()
        
        if not promo:
            return {"success": False, "error": "Промокод не найден"}
        
        promo_id = promo[0]
        
        # Получаем историю активаций и пополнений (фильтруем topup < 10)
        cursor.execute("""
            SELECT ph.action_type, ph.amount, ph.created_at, ph.user_id, u.username, u.avatar_url
            FROM promo_history ph
            LEFT JOIN users u ON ph.user_id = u.id
            WHERE ph.promo_id = ?
            AND (ph.action_type != 'topup' OR ph.amount >= 10)
            ORDER BY ph.created_at DESC
            LIMIT 100
        """, (promo_id,))
        
        history = []
        for row in cursor.fetchall():
            action_type, amount, created_at, ref_user_id, username, avatar_url = row
            history.append({
                "actionType": action_type,
                "amount": amount,
                "createdAt": created_at,
                "userId": ref_user_id,
                "username": username or f"User{ref_user_id}",
                "avatarUrl": avatar_url
            })
        
        return {
            "success": True,
            "history": history
        }
        
    except Exception as e:
        print(f"Error getting promo history: {e}")
        return {"success": False, "error": "Ошибка получения истории"}
    finally:
        conn.close()

@router.post("/rename")
async def rename_promocode(request: RenameRequest):
    """Переименование промокода (создание именного)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = user_data['id']
    new_name = sanitize_promo_name(request.newName)
    
    # Серверная валидация: только буквы, цифры, _ и -
    import re
    if not re.match(r'^[A-Za-z0-9_-]+$', new_name):
        return {"success": False, "error": "Только буквы, цифры, _ и -"}
    
    if len(new_name) < 3:
        return {"success": False, "error": "Минимум 3 символа"}
    
    if len(new_name) > 16:
        return {"success": False, "error": "Максимум 16 символов"}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем минимальное количество рефералов из настроек
        cursor.execute("SELECT value FROM settings WHERE key = 'custom_promo_refs_required'")
        setting = cursor.fetchone()
        required_refs = int(setting[0]) if setting else 10
        
        # Получаем текущий промокод пользователя (только тип 'ref', не 'refCustom')
        cursor.execute(
            "SELECT id, promo, invited_count, type FROM promocodes WHERE owner = ? AND type = 'ref'",
            (user_id,)
        )
        current_promo = cursor.fetchone()
        
        if not current_promo:
            # Проверим, может уже есть именной
            cursor.execute(
                "SELECT type FROM promocodes WHERE owner = ? AND type = 'refCustom'",
                (user_id,)
            )
            if cursor.fetchone():
                return {"success": False, "error": "Именной промокод уже создан"}
            return {"success": False, "error": "У вас нет промокода"}
        
        promo_id, old_code, invited_count, promo_type = current_promo
        
        # Проверяем количество приглашенных
        if invited_count < required_refs:
            return {"success": False, "error": f"Нужно {required_refs} приглашенных ({invited_count}/{required_refs})"}
        
        # Проверяем, не занято ли новое имя
        cursor.execute(
            "SELECT id FROM promocodes WHERE promo = ? AND owner != ?",
            (new_name, user_id)
        )
        if cursor.fetchone():
            return {"success": False, "error": "Это название уже занято"}
        
        # Обновляем промокод - меняем название и тип на 'refCustom' (ID в activated_promocodes не меняется)
        cursor.execute(
            "UPDATE promocodes SET promo = ?, type = 'refCustom' WHERE id = ?",
            (new_name, promo_id)
        )
        
        conn.commit()
        
        return {
            "success": True,
            "promoCode": new_name,
            "message": "Промокод переименован"
        }
        
    except Exception as e:
        conn.rollback()
        print(f"Error renaming promocode: {e}")
        return {"success": False, "error": "Ошибка переименования промокода"}
    finally:
        conn.close()
