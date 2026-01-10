
import sqlite3
import os

DB_PATH = os.path.abspath("../users.db")

def check_gifts():
    try:
        if not os.path.exists(DB_PATH):
            print(f"❌ DB not found at {DB_PATH}")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("--- Checking shop_gifts ---")
        cursor.execute("SELECT count(*) FROM shop_gifts")
        total = cursor.fetchone()[0]
        print(f"Total gifts: {total}")
        
        cursor.execute("SELECT count(*) FROM shop_gifts WHERE ton_price IS NOT NULL AND ton_price > 0")
        with_price = cursor.fetchone()[0]
        print(f"Gifts with valid price: {with_price}")
        
        if total > 0 and with_price == 0:
            print("⚠️ Reason for empty shop: No gifts have 'ton_price' set.")
        
        cursor.execute("SELECT slug, message_id, ton_price FROM shop_gifts LIMIT 5")
        for row in cursor.fetchall():
            print(f"Sample: {row}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_gifts()
