from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
from datetime import datetime
from app.config import BOT_TOKEN, ADMIN_IDS, DB_PATH
from app.utils.validate import validate_init_data

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
async def validate(request: ValidateRequest):
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
        username = user.get('username', '')
        # Получаем URL аватарки из фото (если есть)
        photo_url = user.get('photo_url', '')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем режим технических работ
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        maintenance_result = cursor.fetchone()
        
        # Если режим включен и пользователь не админ - блокируем
        if maintenance_result and maintenance_result[0] == '1':
            if user_id not in ADMIN_IDS:
                conn.close()
                print(f"[MAINTENANCE] User {user_id} blocked during maintenance in validate")
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Технические работы",
                        "message": "Ведутся технические работы. Попробуйте позже.",
                        "maintenance": True
                    }
                )
            else:
                print(f"[MAINTENANCE] Admin {user_id} allowed during maintenance in validate")
        
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            is_banned = bool(result[0])
            # Обновляем username и avatar_url при каждом логине
            cursor.execute(
                "UPDATE users SET username = ?, avatar_url = ? WHERE id = ?",
                (username, photo_url, user_id)
            )
            conn.commit()
        else:
            cursor.execute(
                "INSERT INTO users (id, username, avatar_url, creation_date, is_banned) VALUES (?, ?, ?, ?, 0)",
                (user_id, username, photo_url, datetime.now().isoformat())
            )
            conn.commit()
            is_banned = False
        
        conn.close()
        
        return {"valid": True, "isBanned": is_banned}
    except Exception:
        return {"valid": False, "isBanned": False}

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
            
            is_admin = user_id in ADMIN_IDS
            print(f"check-admin: user_id={user_id}, is_admin={is_admin}")
            return {"valid": True, "isAdmin": is_admin}
        
        print("check-admin: No user data")
        return {"valid": True, "isAdmin": False}
    except Exception as e:
        print(f"check-admin ERROR: {e}")
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        conn = sqlite3.connect(DB_PATH)
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        conn = sqlite3.connect(DB_PATH)
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        is_banned = bool(result[0]) if result else False
        return {"valid": True, "isBanned": is_banned}
    except Exception:
        return {"valid": False, "isBanned": False}
