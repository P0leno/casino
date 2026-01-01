import sqlite3
import os
import sys

# Add parent directory to path to import app modules if needed, 
# but here we just need raw DB access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.getenv("DB_PATH", "users.db")

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        settings_to_add = [
            ('withdraw_regular_enabled', '1', 'Авто-выдача обычных подарков'),
            ('withdraw_nft_enabled', '1', 'Авто-выдача NFT подарков')
        ]
        
        added_count = 0
        for key, val, desc in settings_to_add:
            # Check if exists
            cursor.execute("SELECT 1 FROM settings WHERE key = ?", (key,))
            if cursor.fetchone():
                print(f"Setting '{key}' already exists. Skipping.")
            else:
                cursor.execute("""
                    INSERT INTO settings (key, value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, val, desc))
                print(f"Added setting: {key} = {val}")
                added_count += 1
        
        conn.commit()
        conn.close()
        print(f"Migration complete. Added {added_count} new settings.")
        
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
