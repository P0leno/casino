from fastapi import APIRouter, Request
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
async def validate(validate_req: ValidateRequest, request: Request):
    is_valid = validate_init_data(validate_req.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isBanned": False}
    
    # Извлекаем IP адрес и User-Agent
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Проверяем режим технических работ ПЕРВЫМ делом
    print("=" * 80)
    print("[VALIDATE] Starting maintenance check...")
    try:
        parsed = parse_qs(validate_req.initData)
        user_data = parsed.get('user', [''])[0]
        
        if user_data:
            user = json.loads(user_data)
            user_id = user.get('id')
            
            print(f"[VALIDATE] Parsed user_id: {user_id}")
            print(f"[VALIDATE] ADMIN_IDS: {ADMIN_IDS}")
            print(f"[VALIDATE] DB_PATH: {DB_PATH}")
            
            # Проверяем maintenance_mode
            conn = None
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Сначала проверим что таблица существует
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
                table_exists = cursor.fetchone()
                print(f"[VALIDATE] Settings table exists: {table_exists is not None}")
                
                if table_exists:
                    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
                    maintenance_result = cursor.fetchone()
                    print(f"[VALIDATE] Maintenance result from DB: {maintenance_result}")
                    
                    is_admin = user_id in ADMIN_IDS
                    print(f"[VALIDATE] user_id={user_id}, maintenance_value={maintenance_result[0] if maintenance_result else 'None'}, is_admin={is_admin}")
                    
                    # Если режим включен и пользователь не админ - блокируем
                    if maintenance_result and maintenance_result[0] == '1':
                        if not is_admin:
                            print(f"[MAINTENANCE] ⛔ User {user_id} BLOCKED during maintenance - returning 503")
                            return JSONResponse(
                                status_code=503,
                                content={
                                    "detail": "Технические работы",
                                    "message": "Ведутся технические работы. Попробуйте позже.",
                                    "maintenance": True
                                }
                            )
                        else:
                            print(f"[MAINTENANCE] ✅ Admin {user_id} ALLOWED during maintenance")
                    else:
                        print(f"[VALIDATE] Maintenance is OFF or not found, continuing...")
                else:
                    print(f"[VALIDATE] WARNING: settings table does not exist!")
            finally:
                if conn:
                    conn.close()
                    print(f"[VALIDATE] Maintenance DB connection closed")
        else:
            print(f"[VALIDATE] No user data in initData")
    except Exception as e:
        print(f"[MAINTENANCE] ❌ ERROR checking maintenance: {e}")
        import traceback
        traceback.print_exc()
    
    print("[VALIDATE] Maintenance check completed, continuing to normal flow...")
    print("=" * 80)
    
    try:
        parsed = parse_qs(validate_req.initData)
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
        
        cursor.execute("SELECT is_banned, balance, bonus_balance, ip_addresses, user_agents FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            is_banned = bool(result[0])
            balance = result[1] if result[1] is not None else 0
            bonus_balance = result[2] if result[2] is not None else 0
            
            # Обновляем списки IP и User-Agent
            ip_list = json.loads(result[3]) if result[3] else []
            ua_list = json.loads(result[4]) if result[4] else []
            
            # Добавляем в начало, удаляем дубликаты, ограничиваем до 6
            if client_ip not in ip_list:
                ip_list.insert(0, client_ip)
                ip_list = ip_list[:6]
            
            if user_agent not in ua_list:
                ua_list.insert(0, user_agent)
                ua_list = ua_list[:6]
            
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
            "balance": balance,
            "bonusBalance": bonus_balance
        }
    except Exception as e:
        print(f"[VALIDATE] ❌ ERROR in main validation logic: {e}")
        import traceback
        traceback.print_exc()
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
