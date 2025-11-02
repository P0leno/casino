import sqlite3
from datetime import datetime
from app.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            creation_date TEXT NOT NULL,
            is_banned INTEGER DEFAULT 0,
            last_spin_date TEXT,
            inventory TEXT DEFAULT '[]',
            balance INTEGER DEFAULT 0,
            bonus_balance INTEGER DEFAULT 0,
            last_spin_notification TEXT
        )
    """)
    
    # Автоматическая миграция: добавление last_spin_notification если его нет
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'last_spin_notification' not in columns:
            print("⚙️  Миграция: добавление поля last_spin_notification...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_spin_notification TEXT")
            conn.commit()
            print("✅ Миграция завершена: last_spin_notification добавлен")
    except Exception as e:
        print(f"⚠️  Ошибка миграции last_spin_notification: {e}")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            mode TEXT DEFAULT 'free_spin',
            paw_min INTEGER DEFAULT 0,
            paw_max INTEGER DEFAULT 0,
            star_min INTEGER DEFAULT 1,
            star_max INTEGER DEFAULT 5,
            UNIQUE(gift_name, mode)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paid_spin_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            paw_min INTEGER DEFAULT 0,
            paw_max INTEGER DEFAULT 0,
            star_min INTEGER DEFAULT 1,
            star_max INTEGER DEFAULT 5
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL,
            gift_id TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crash_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_multiplier REAL DEFAULT 1000.0
        )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO crash_settings (id, max_multiplier) VALUES (1, 1000.0)")
    
    # Данные для бесплатного спина
    # star_min/star_max - только для 'star', paw_min/paw_max - только для 'paw'
    free_spin_gifts = [
        ('bear', 10.0, 1.0, 0, 0, 0, 0),
        ('cake', 10.0, 0.0, 0, 0, 0, 0),
        ('cup', 10.0, 0.0, 0, 0, 0, 0),
        ('diamond', 10.0, 0.0, 0, 0, 0, 0),
        ('flowers', 10.0, 0.0, 0, 0, 0, 0),
        ('gift', 10.0, 0.01, 0, 0, 0, 0),
        ('heart', 10.0, 1.0, 0, 0, 0, 0),
        ('ring', 10.0, 0.0, 0, 0, 0, 0),
        ('rocket', 10.0, 0.0, 0, 0, 0, 0),
        ('rose', 10.0, 0.0, 0, 0, 0, 0),
        ('bottle', 10.0, 0.0, 0, 0, 0, 0),
        ('paw', 10.0, 90.0, 1, 7, 0, 0),
        ('star', 10.0, 7.0, 0, 0, 1, 5)
    ]
    
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in free_spin_gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'free_spin', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
    
    # Данные для платного спина (бомж кейс) за 5 звезд
    # star_min/star_max - только для 'star', paw_min/paw_max - только для 'paw'
    bomzcase_gifts = [
        ('bear', 10.0, 1.0, 0, 0, 0, 0),
        ('heart', 10.0, 1.0, 0, 0, 0, 0),
        ('rose', 10.0, 0.0, 0, 0, 0, 0),
        ('gift', 10.0, 0.01, 0, 0, 0, 0),
        ('paw', 10.0, 90.0, 1, 7, 0, 0),
        ('star', 20.0, 7.0, 0, 0, 1, 4)
    ]
    
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in bomzcase_gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'bomzcase', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
    
    prices = [
        ('bear', 15, '5170233102089322756'),
        ('cake', 50, '5170144170496491616'),
        ('cup', 100, '5168043875654172773'),
        ('diamond', 100, '5170521118301225164'),
        ('flowers', 50, '5170314324215857265'),
        ('gift', 25, '5170250947678437525'),
        ('heart', 15, '5170145012310081615'),
        ('ring', 100, '5170690322832818290'),
        ('rocket', 50, '5170564780938756245'),
        ('rose', 25, '5168103777563050263'),
        ('bottle', 0, '6028601630662853006')
    ]
    
    for gift_name, price, gift_id in prices:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_prices (gift_name, price, gift_id) VALUES (?, ?, ?)",
            (gift_name, price, gift_id)
        )
    
    conn.commit()
    conn.close()
