import os
import sys
import sqlite3
import json

# Add server directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(os.path.dirname(current_dir), 'server')
sys.path.append(server_dir)

from app.utils.redis_client import redis_client as r
from app.utils.database import DB_PATH as SERVER_DB_PATH

# Overwrite DB_PATH to point correctly if needed, or rely on imported one if absolute
# But app.utils.database usually uses relative "./users.db".
# We need to construct absolute path to users.db
DB_PATH = os.path.join(server_dir, "users.db")

def sync_purchased_slugs():
    print("Connecting to Database at:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Fetching all user inventories...")
    cursor.execute("SELECT inventory FROM users")
    
    all_slugs = set()
    rows = cursor.fetchall()
    
    print(f"Scanning {len(rows)} users...")
    
    for row in rows:
        if row[0]:
            try:
                inventory = json.loads(row[0])
                for slug in inventory:
                    all_slugs.add(slug)
            except json.JSONDecodeError:
                continue
                
    print(f"Found {len(all_slugs)} unique purchased slugs.")
    
    if all_slugs:
        # Check redis connection first
        try:
            r.ping()
            print("Redis connected.")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return

        r.delete("shop:purchased_slugs")
        r.sadd("shop:purchased_slugs", *all_slugs)
        print("Updated Redis key 'shop:purchased_slugs'")
    else:
        print("No purchased slugs found.")
        
    conn.close()
    print("Done.")

if __name__ == "__main__":
    sync_purchased_slugs()
