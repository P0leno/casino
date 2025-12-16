from app.utils.database import get_db_connection, DB_PATH
#!/usr/bin/env python3
"""
Миграция для добавления поля last_spin_notification
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from app.config import DB_PATH

def migrate():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔄 Начинаем миграцию: добавление last_spin_notification...")
    
    try:
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_spin_notification' not in columns:
            print("Добавление поля last_spin_notification...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_spin_notification TEXT")
            conn.commit()
            print("✓ Поле last_spin_notification добавлено")
        else:
            print("✓ Поле last_spin_notification уже существует")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    finally:
        conn.close()
    
    print("✅ Миграция завершена!")

if __name__ == "__main__":
    migrate()
