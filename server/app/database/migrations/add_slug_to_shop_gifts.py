#!/usr/bin/env python3
"""
Миграция: добавление колонки slug в shop_gifts
"""
import sqlite3
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.config import DB_PATH

def migrate():
    """Добавляет колонку slug в таблицу shop_gifts"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем существование колонки
        cursor.execute("PRAGMA table_info(shop_gifts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'slug' not in columns:
            print("➕ Добавляем колонку slug...")
            cursor.execute("ALTER TABLE shop_gifts ADD COLUMN slug TEXT")
            conn.commit()
            print("✅ Колонка slug добавлена")
        else:
            print("ℹ️  Колонка slug уже существует")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
