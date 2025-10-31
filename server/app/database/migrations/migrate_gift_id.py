import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.config import DB_PATH

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(gift_prices)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'gift_id' not in columns:
            print("Adding gift_id column to gift_prices...")
            cursor.execute("ALTER TABLE gift_prices ADD COLUMN gift_id TEXT")
            conn.commit()
            print("✓ gift_id column added successfully")
        else:
            print("✓ gift_id column already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
