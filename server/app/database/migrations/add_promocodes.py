import sqlite3
import os

def run_migration():
    """Добавляет таблицу promocodes и поле activated_promocodes в users"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gifts.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Создаем таблицу promocodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promo TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'ref',
                xp INTEGER NOT NULL DEFAULT 0,
                owner INTEGER NOT NULL,
                reward INTEGER NOT NULL DEFAULT 25,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Таблица promocodes создана")
        
        # Проверяем, есть ли уже колонка activated_promocodes
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'activated_promocodes' not in columns:
            # Добавляем поле activated_promocodes в таблицу users
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN activated_promocodes TEXT DEFAULT '[]'
            ''')
            print("✓ Поле activated_promocodes добавлено в таблицу users")
        else:
            print("⚠ Поле activated_promocodes уже существует")
        
        if 'refbalance' not in columns:
            # Добавляем поле refbalance в таблицу users
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN refbalance INTEGER DEFAULT 0
            ''')
            print("✓ Поле refbalance добавлено в таблицу users")
        else:
            print("⚠ Поле refbalance уже существует")
        
        conn.commit()
        print("✓ Миграция успешно выполнена")
        
    except Exception as e:
        print(f"✗ Ошибка при выполнении миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
