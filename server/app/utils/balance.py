"""
Утилита для работы с балансом пользователей
"""
import sqlite3
from app.config import DB_PATH

def get_user_balance(user_id: int) -> dict:
    """
    Получает баланс пользователя из БД
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        dict: {"balance": int, "bonusBalance": int}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance, bonus_balance FROM users WHERE id = ?", 
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "balance": result[0] if result[0] is not None else 0,
                "bonusBalance": result[1] if result[1] is not None else 0
            }
        else:
            return {"balance": 0, "bonusBalance": 0}
    except Exception as e:
        print(f"[BALANCE] Error getting user balance: {e}")
        import traceback
        traceback.print_exc()
        return {"balance": 0, "bonusBalance": 0}
