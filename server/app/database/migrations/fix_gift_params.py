from app.utils.database import get_db_connection, DB_PATH
"""
Миграция: Очистка параметров star_min/star_max и paw_min/paw_max
- star_min/star_max остаются только для подарка 'star'
- paw_min/paw_max остаются только для подарка 'paw'
- Для остальных подарков обнуляем эти параметры (они не используются)
"""

import sqlite3
import os

# Путь к базе данных (относительно корня проекта)
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(script_dir, '../../../users.db')

def migrate():
    print("🔄 Запуск миграции: Очистка параметров star_min/star_max и paw_min/paw_max...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Обнуляем star_min и star_max для всех подарков кроме 'star'
        cursor.execute("""
            UPDATE gift_chances 
            SET star_min = 0, star_max = 0 
            WHERE gift_name != 'star'
        """)
        updated_star = cursor.rowcount
        print(f"  ✅ Обнулены star_min/star_max для {updated_star} записей (кроме 'star')")
        
        # Обнуляем paw_min и paw_max для всех подарков кроме 'paw'
        cursor.execute("""
            UPDATE gift_chances 
            SET paw_min = 0, paw_max = 0 
            WHERE gift_name != 'paw'
        """)
        updated_paw = cursor.rowcount
        print(f"  ✅ Обнулены paw_min/paw_max для {updated_paw} записей (кроме 'paw')")
        
        conn.commit()
        print("✅ Миграция завершена успешно!")
        
        # Покажем результат
        print("\n📊 Текущее состояние gift_chances:")
        cursor.execute("""
            SELECT gift_name, mode, paw_min, paw_max, star_min, star_max 
            FROM gift_chances 
            ORDER BY mode, gift_name
        """)
        for row in cursor.fetchall():
            gift_name, mode, paw_min, paw_max, star_min, star_max = row
            print(f"  {mode:12} | {gift_name:8} | paw: {paw_min}-{paw_max} | star: {star_min}-{star_max}")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
