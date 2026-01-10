import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "server/users.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    print("Creating sold_gifts table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sold_gifts (
        slug TEXT PRIMARY KEY,
        user_id INTEGER,
        purchased_at TEXT
    )
    """)
    
    # Populate from inventory
    print("Scanning users inventory...")
    cursor.execute("SELECT id, inventory FROM users")
    rows = cursor.fetchall()
    
    count = 0
    skipped = 0
    
    for user_id, inventory_json in rows:
        if not inventory_json:
            continue
            
        try:
            inventory = json.loads(inventory_json)
            for slug in inventory:
                try:
                    # Insert ignore duplicate
                    cursor.execute("""
                        INSERT OR IGNORE INTO sold_gifts (slug, user_id, purchased_at)
                        VALUES (?, ?, ?)
                    """, (slug, user_id, datetime.now().isoformat()))
                    count += 1
                except sqlite3.Error as e:
                    print(f"Error inserting {slug}: {e}")
        except json.JSONDecodeError:
            skipped += 1
            
    conn.commit()
    conn.close()
    print(f"Migration done. Added {count} sold gifts. Skipped {skipped} malformed JSONs.")

if __name__ == "__main__":
    migrate()
