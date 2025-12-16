"""
Эндпоинт для проверки режима технических работ с учетом прав админа
"""

from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
from app.config import DB_PATH, BOT_TOKEN, ADMIN_IDS
from app.utils.validate import validate_init_data

router = APIRouter(prefix="/api", tags=["maintenance"])

class CheckMaintenanceRequest(BaseModel):
    initData: str

@router.post("/check-user-maintenance")
async def check_user_maintenance(request: CheckMaintenanceRequest):
    """
    Проверить нужно ли блокировать пользователя из-за режима технических работ
    
    Возвращает:
    - shouldBlock: true если пользователь НЕ админ и режим включен
    - shouldBlock: false если админ или режим выключен
    """
    print("=" * 80)
    print("[MAINTENANCE CHECK] Starting...")
    
    try:
        # Проверяем валидность initData
        is_valid = validate_init_data(request.initData, BOT_TOKEN)
        if not is_valid:
            print("[MAINTENANCE CHECK] Invalid initData - blocking")
            return {"shouldBlock": False, "maintenance": False}
        
        # Парсим user_id
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            print("[MAINTENANCE CHECK] No user data - not blocking")
            return {"shouldBlock": False, "maintenance": False}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        print(f"[MAINTENANCE CHECK] User ID: {user_id} (type: {type(user_id)})")
        print(f"[MAINTENANCE CHECK] ADMIN_IDS: {ADMIN_IDS}")
        
        # Проверяем админа - ВАЖНО: приводим типы
        # user_id может быть int, ADMIN_IDS тоже int
        is_admin = int(user_id) in ADMIN_IDS
        
        print(f"[MAINTENANCE CHECK] Is admin check: int({user_id}) in {ADMIN_IDS} = {is_admin}")
        
        # Проверяем режим в БД
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("[MAINTENANCE CHECK] Settings table not found - not blocking")
            conn.close()
            return {"shouldBlock": False, "maintenance": False}
        
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        result = cursor.fetchone()
        conn.close()
        
        maintenance_enabled = result and result[0] == '1'
        print(f"[MAINTENANCE CHECK] Maintenance enabled: {maintenance_enabled}")
        
        # Решение: блокировать если режим включен И пользователь не админ
        should_block = maintenance_enabled and not is_admin
        
        print(f"[MAINTENANCE CHECK] Decision: shouldBlock={should_block}")
        print("=" * 80)
        
        return {
            "shouldBlock": should_block,
            "maintenance": maintenance_enabled,
            "isAdmin": is_admin
        }
        
    except Exception as e:
        print(f"[MAINTENANCE CHECK] Error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return {"shouldBlock": False, "maintenance": False}
