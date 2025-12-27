import sqlite3
import os
import sys

# Добавляем путь к server для импорта app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.support_db import init_support_db, get_support_db_connection
from app.utils.database import get_db_connection

def migrate_data():
    print("🔄 Starting migration to support.db...")
    
    # 1. Initialize new DB
    init_support_db()
    
    old_conn = get_db_connection()
    old_cursor = old_conn.cursor()
    
    new_conn = get_support_db_connection()
    new_cursor = new_conn.cursor()
    
    # 2. Migrate Users (only support-related fields)
    print("👥 Migrating users...")
    
    # Select users who have relevant support data (ban, ip, ua) or active dialogs (if any exist)
    # Since user mentioned dialogs might be deleted, we rely on fields presence too.
    query = """
    SELECT id, username, support_banned, support_banned_until, ip_addresses, user_agents 
    FROM users 
    WHERE support_banned = 1 
       OR (ip_addresses IS NOT NULL AND ip_addresses != '[]')
       OR (user_agents IS NOT NULL AND user_agents != '[]')
       OR id IN (SELECT user_id FROM support_dialogs)
    """
    try:
        old_cursor.execute(query)
        users = old_cursor.fetchall()
    except Exception as e:
        print(f"⚠️  Could not filter by support_dialogs (table might be missing), fetching users with data only: {e}")
        query_fallback = """
        SELECT id, username, support_banned, support_banned_until, ip_addresses, user_agents 
        FROM users 
        WHERE support_banned = 1 
           OR (ip_addresses IS NOT NULL AND ip_addresses != '[]')
           OR (user_agents IS NOT NULL AND user_agents != '[]')
        """
        old_cursor.execute(query_fallback)
        users = old_cursor.fetchall()
    
    count = 0
    for u in users:
        # u: id, username, support_banned, support_banned_until, ip_addresses, user_agents
        new_cursor.execute("""
        INSERT OR REPLACE INTO users (id, username, support_banned, support_banned_until, ip_addresses, user_agents)
        VALUES (?, ?, ?, ?, ?, ?)
        """, u)
        count += 1
        
    print(f"✅ Migrated/Updated {count} users")
    new_conn.commit()
    
    # 3. Migrate Settings
    print("⚙️  Migrating support settings...")
    try:
        old_cursor.execute("SELECT key, value, updated_at FROM support_settings")
        settings = old_cursor.fetchall()
        for s in settings:
            new_cursor.execute("INSERT OR REPLACE INTO support_settings (key, value, updated_at) VALUES (?, ?, ?)", s)
        print(f"✅ Migrated {len(settings)} settings")
    except Exception as e:
        print(f"⚠️  Skipping settings migration (table might be missing): {e}")

    # 4. Migrate Dialogs & Messages (If they exist)
    print("� Migrating dialogs and messages...")
    try:
        old_cursor.execute("SELECT dialog_id, user_id, username, category, status, created_at, closed_at, last_response_at, isPriority FROM support_dialogs")
        dialogs = old_cursor.fetchall()
        
        d_count = 0
        m_count = 0
        
        for d in dialogs:
            # Check if user exists in support.db (foreign key constraint)
            new_cursor.execute("SELECT 1 FROM users WHERE id = ?", (d[1],))
            if not new_cursor.fetchone():
                # User might not have been migrated if they had no IP/UA/Ban and query filtered them out?
                # But our query includes "OR id IN (SELECT user_id FROM support_dialogs)"
                # Just in case, insert stub user to allow dialog migration
                new_cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (d[1], d[2]))
            
            new_cursor.execute("""
            INSERT OR REPLACE INTO support_dialogs (dialog_id, user_id, username, category, status, created_at, closed_at, last_response_at, isPriority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, d)
            d_count += 1
            
            # Migrate messages for this dialog
            old_cursor.execute("SELECT sender_type, sender_name, message_text, photo_path, sent_at FROM dialog_messages WHERE dialog_id = ?", (d[0],))
            messages = old_cursor.fetchall()
            
            for m in messages:
                new_cursor.execute("""
                INSERT OR REPLACE INTO dialog_messages (dialog_id, sender_type, sender_name, message_text, photo_path, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (d[0],) + m)
                m_count += 1
                
        print(f"✅ Migrated {d_count} dialogs and {m_count} messages")
    except Exception as e:
        print(f"⚠️  Skipping dialogs migration (table hidden/deleted or empty): {e}")
    # 6. Migrate Support Messages (if any)
    print("📨 Migrating support_messages...")
    try:
        old_cursor.execute("SELECT id, dialog_id, from_user, message_text, photo_id, created_at FROM support_messages")
        sms = old_cursor.fetchall()
        for sm in sms:
            new_cursor.execute("""
                INSERT OR REPLACE INTO support_messages 
                (id, dialog_id, from_user, message_text, photo_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, sm)
        print(f"✅ Migrated {len(sms)} support messages")
    except Exception as e:
        print(f"⚠️  Error migrating support messages (maybe table didn't exist): {e}")
        
    new_conn.commit()
    new_conn.close()
    old_conn.close()
    
    print("🎉 Migration completed successfully!")

if __name__ == "__main__":
    migrate_data()
