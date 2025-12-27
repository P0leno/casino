import sqlite3
from app.config import SUPPORT_DB_PATH

def get_support_db_connection():
    conn = sqlite3.connect(SUPPORT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_support_db():
    conn = get_support_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table for support
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            support_banned INTEGER DEFAULT 0,
            support_banned_until TEXT,
            ip_addresses TEXT DEFAULT '[]',
            user_agents TEXT DEFAULT '[]'
        )
    """)
    
    # 2. Support Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    
    # 3. Support Dialogs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_dialogs (
            dialog_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            last_response_at TIMESTAMP,
            isPriority INTEGER DEFAULT 0
        )
    """)
    
    # 4. Dialog Messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            sender_name TEXT,
            message_text TEXT,
            photo_path TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dialog_id) REFERENCES support_dialogs(dialog_id)
        )
    """)
    
    # 5. Support Messages (Legacy/Alternative?)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER NOT NULL,
            from_user INTEGER NOT NULL,
            message_text TEXT,
            photo_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dialog_id) REFERENCES support_dialogs(dialog_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ Support DB initialized at {SUPPORT_DB_PATH}")
