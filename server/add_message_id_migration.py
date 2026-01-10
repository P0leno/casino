
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "users.db")

def migrate():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(shop_gifts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'message_id' not in columns:
            print("Adding message_id column to shop_gifts...")
            cursor.execute("ALTER TABLE shop_gifts ADD COLUMN message_id INTEGER")
            conn.commit()
            print("✅ message_id column added successfully.")
        else:
            print("⚠️ message_id column already exists.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
