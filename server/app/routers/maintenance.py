"""
Эндпоинт для проверки режима технических работ
Доступен всем без авторизации
"""

from fastapi import APIRouter
from app.utils.database import get_db_connection, DB_PATH
from app.utils.error_logger import send_error_log
import sqlite3
from app.config import DB_PATH

router = APIRouter(prefix="/api", tags=["maintenance"])

@router.get("/check-maintenance")
async def check_maintenance():
    """
    Проверить включен ли режим технических работ
    Доступен всем без авторизации
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        result = cursor.fetchone()
        conn.close()
        
        enabled = result[0] == '1' if result else False
        
        return {
            "maintenance": enabled,
            "message": "Ведутся технические работы. Попробуйте позже." if enabled else ""
        }
        
    except Exception as e:
        print(f"Error checking maintenance: {e}")
        await send_error_log(e, "maintenance.py: check_maintenance")
        return {
            "maintenance": False,
            "message": ""
        }
