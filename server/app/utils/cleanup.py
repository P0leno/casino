import sqlite3
from app.utils.database import get_db_connection

def delete_blocked_user(user_id: int):
    """
    Удаляет пользователя и его данные из БД, если он заблокировал бота.
    Удаляет:
    1. Промокоды пользователя
    2. Историю промокодов (связанную с его промокодами и его активациями)
    3. Самого пользователя (users)
    4. Purchased gifts (если есть)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print(f"🚫 [BLOCK] Deleting user {user_id} (Blocked bot)...")

        # 1. Получаем ID промокодов пользователя
        cursor.execute("SELECT id, promo FROM promocodes WHERE owner = ?", (user_id,))
        promos = cursor.fetchall()
        promo_ids = [p[0] for p in promos]
        promo_codes = [p[1] for p in promos]

        # 2. Удаляем историю активаций ЭТИХ промокодов (другими людьми)
        if promo_ids:
            # Безопасное формирование плейсхолдеров
            placeholders = ','.join('?' * len(promo_ids))
            query = f"DELETE FROM promo_history WHERE promo_id IN ({placeholders})"
            cursor.execute(query, promo_ids)
            print(f"   Deleted history for {len(promo_ids)} promos owned by user")

        # 3. Удаляем историю активаций САМИМ пользователем (чужих промокодов)
        cursor.execute("DELETE FROM promo_history WHERE user_id = ?", (user_id,))
        print(f"   Deleted activation history by user")

        # 4. Удаляем сами промокоды пользователя
        cursor.execute("DELETE FROM promocodes WHERE owner = ?", (user_id,))
        print(f"   Deleted {len(promo_codes)} promos: {promo_codes}")

        # 5. Удаляем пользователя из users
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        print(f"   Deleted user from users table")
        
        # 6. Удаляем из purchased_gifts (на всякий случай, если есть)
        try:
            cursor.execute("DELETE FROM purchased_gifts WHERE user_id = ?", (user_id,))
        except Exception:
            pass # Таблицы может не быть, это нормально

        conn.commit()
        conn.close()

        print(f"✅ [BLOCK] User {user_id} completely deleted.")
        return True

    except Exception as e:
        print(f"❌ [BLOCK] Error deleting user {user_id}: {e}")
        return False
