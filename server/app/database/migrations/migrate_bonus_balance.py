import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.config import DB_PATH

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли колонка
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'bonus_balance' not in columns:
            print("Adding bonus_balance column...")
            cursor.execute("ALTER TABLE users ADD COLUMN bonus_balance INTEGER DEFAULT 0")
            conn.commit()
            print("✓ bonus_balance column added successfully")
        else:
            print("✓ bonus_balance column already exists")
    except Exception as e:
        print(f"✗ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
