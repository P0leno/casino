
import sqlite3
import os

# Point to users.db
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shell', 'users.db')

def migrate():
    print(f"Migrating database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Error: users.db not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Creating nft_invoices table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nft_invoices (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                slug TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                payment_charge_id TEXT
            )
        """)
        
        # Verify
        cursor.execute("PRAGMA table_info(nft_invoices)")
        columns = cursor.fetchall()
        print("Table structure:", columns)
        
        conn.commit()
        print("Migration successful.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
