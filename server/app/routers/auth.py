from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from datetime import datetime
from app.config import BOT_TOKEN, DB_PATH
from app.utils.validate import validate_init_data
from app.utils.redis_models import RedisSettings
from app.utils.database import get_db_connection
from app.utils.error_logger import send_error_log

router = APIRouter(prefix="/api", tags=["auth"])

class ValidateRequest(BaseModel):
    initData: str

class BanRequest(BaseModel):
    initData: str
    targetUserId: int

# Вспомогательная функция для получения user_data из initData
def verify_init_data(init_data: str):
    """
    Проверяет initData и возвращает user_data с telegram_id
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
        # Добавляем telegram_id для совместимости
        user_data['telegram_id'] = user_data.get('id')
        return user_data
    except:
        return None

@router.post("/validate")
async def validate(validate_req: ValidateRequest, request: Request):
    is_valid = validate_init_data(validate_req.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isBanned": False}
    
    # Извлекаем IP адрес (приоритет: CF-Connecting-IP > X-Real-IP > X-Forwarded-For > client.host)
    client_ip = (
        request.headers.get("cf-connecting-ip") or
        request.headers.get("x-real-ip") or
        request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
        (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        parsed = parse_qs(validate_req.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "isBanned": False, "isAdmin": False, "maintenance": False}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        username = user.get('username', '')
        is_admin = RedisSettings.is_admin(user_id)
        
        # Проверяем режим тех.работ из Redis
        maintenance_mode = RedisSettings.get_bool('maintenance_mode', False)
        if maintenance_mode and not is_admin:
            return {
                "valid": True,
                "isBanned": False,
                "isAdmin": False,
                "maintenance": True,
                "message": "Ведутся технические работы. Попробуйте позже."
            }
        # Получаем URL аватарки из фото (если есть)
        photo_url = user.get('photo_url', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_banned, balance, bonus_balance, ip_addresses, user_agents FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            is_banned = bool(result[0])
            balance = result[1] if result[1] is not None else 0
            bonus_balance = result[2] if result[2] is not None else 0
            
            # Обновляем списки IP и User-Agent
            ip_list = json.loads(result[3]) if result[3] else []
            ua_list = json.loads(result[4]) if result[4] else []
            
            # Перемещаем в начало (удаляем если есть, добавляем первым), ограничиваем до 5
            if client_ip in ip_list:
                ip_list.remove(client_ip)
            ip_list.insert(0, client_ip)
            ip_list = ip_list[:5]
            
            if user_agent in ua_list:
                ua_list.remove(user_agent)
            ua_list.insert(0, user_agent)
            ua_list = ua_list[:5]
            
            # Обновляем username, avatar_url, IP и User-Agent при каждом логине
            cursor.execute(
                "UPDATE users SET username = ?, avatar_url = ?, ip_addresses = ?, user_agents = ? WHERE id = ?",
                (username, photo_url, json.dumps(ip_list), json.dumps(ua_list), user_id)
            )
            conn.commit()
        else:
            # Новый пользователь
            ip_list = [client_ip]
            ua_list = [user_agent]
            
            cursor.execute(
                "INSERT INTO users (id, username, avatar_url, creation_date, is_banned, balance, bonus_balance, ip_addresses, user_agents) VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)",
                (user_id, username, photo_url, datetime.now().isoformat(), json.dumps(ip_list), json.dumps(ua_list))
            )
            conn.commit()
            is_banned = False
            balance = 0
            bonus_balance = 0
        
        conn.close()
        
        return {
            "valid": True, 
            "isBanned": is_banned,
            "isAdmin": is_admin,
            "maintenance": False,
            "balance": balance,
            "bonusBalance": bonus_balance
        }
    except Exception as e:
        print(f"[VALIDATE] ❌ ERROR: {e}")
        await send_error_log(e, "auth.py: validate")
        return {"valid": False, "isBanned": False, "isAdmin": False, "maintenance": False}

@router.post("/check-admin")
async def check_admin(request: ValidateRequest):
    try:
        is_valid = validate_init_data(request.initData, BOT_TOKEN)
        
        if not is_valid:
            print("check-admin: Invalid init data")
            return {"valid": False, "isAdmin": False}
        
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if user_data:
            user = json.loads(user_data)
            user_id = user.get('id')
            
            is_admin = RedisSettings.is_admin(user_id)
            print(f"check-admin: user_id={user_id}, is_admin={is_admin}")
            return {"valid": True, "isAdmin": is_admin}
        
        print("check-admin: No user data")
        return {"valid": True, "isAdmin": False}
    except Exception as e:
        print(f"check-admin ERROR: {e}")
        await send_error_log(e, "auth.py: check_admin")
        return {"valid": False, "isAdmin": False}

@router.post("/ban-user")
async def ban_user(request: BanRequest):
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE id = ?", (request.targetUserId,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (request.targetUserId,))
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, is_banned) VALUES (?, ?, 1)",
                (request.targetUserId, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in ban_user: {e}")
        await send_error_log(e, "auth.py: ban_user")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/unban-user")
async def unban_user(request: BanRequest):
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE id = ?", (request.targetUserId,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (request.targetUserId,))
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, is_banned) VALUES (?, ?, 0)",
                (request.targetUserId, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in ban_user: {e}")
        await send_error_log(e, "auth.py: unban_user")
        return {"success": False, "message": "Ошибка сервера"}

@router.post("/check-ban")
async def check_ban(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isBanned": False}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "isBanned": False}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        is_banned = bool(result[0]) if result else False
        return {"valid": True, "isBanned": is_banned}
    except Exception as e:
        await send_error_log(e, "auth.py: check_ban")
        return {"valid": False, "isBanned": False}
