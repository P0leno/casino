
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "users.db")

def migrate():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price INTEGER DEFAULT 0,
                currency TEXT DEFAULT 'star',
                is_active INTEGER DEFAULT 1
            )
        """)
        print("✅ Table 'cases' created/checked.")
        
        # Seed Data
        cases = [
            ('free_spin', 'Бесплатный', 0, 'none'),
            ('bazmin', 'Бомж кейс', 5, 'star'),
            ('lapik', 'Лапик кейс', 10, 'paw')
        ]
        
        for slug, title, price, currency in cases:
            cursor.execute(
                "INSERT OR IGNORE INTO cases (slug, title, price, currency) VALUES (?, ?, ?, ?)",
                (slug, title, price, currency)
            )
            
        conn.commit()
        print("✅ Initial cases seeded.")
        
        # Verify
        cursor.execute("SELECT * FROM cases")
        rows = cursor.fetchall()
        print("Current Cases:", rows)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
