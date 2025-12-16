"""
Утилита для работы с балансом пользователей
"""
from app.utils.database import get_db_connection

def get_user_balance(user_id: int) -> dict:
    """
    Получает баланс пользователя из БД
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        dict: {"balance": int, "bonusBalance": int}
    """
    try:
        conn = get_db_connection()
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
