"""
API для управления банами пользователей
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.database import get_db_connection, DB_PATH
from app.config import DB_PATH
from app.routers.auth import verify_init_data
from app.utils.error_logger import send_error_log

router = APIRouter()

class CheckBanRequest(BaseModel):
    initData: str

@router.post("/check-ban")
async def check_ban(request: CheckBanRequest):
    """Проверка бана пользователя"""
    try:
        user_data = verify_init_data(request.initData)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid initData")
        
        telegram_id = user_data.get('telegram_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"banned": False}
        
        is_banned = bool(result[0])
        
        return {
            "banned": is_banned,
            "botUsername": "HelpShellBot"  # Для ссылки на бота
        }
    
    except Exception as e:
        print(f"Error checking ban: {e}")
        # Note: HTTPException breaks flow, so we log first
        await send_error_log(e, "ban.py: check_ban")
        raise HTTPException(status_code=500, detail=str(e))
