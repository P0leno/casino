"""
Эндпоинт для проверки режима технических работ
Доступен всем без авторизации
"""

from fastapi import APIRouter
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
        conn = sqlite3.connect(DB_PATH)
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
        return {
            "maintenance": False,
            "message": ""
        }
