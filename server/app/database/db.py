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
            bonus_balance INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            mode TEXT DEFAULT 'free_spin'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL
        )
    """)
    
    gifts = [
        ('bear', 10.0, 10.0),
        ('cake', 10.0, 10.0),
        ('cup', 10.0, 10.0),
        ('diamond', 10.0, 5.0),
        ('flowers', 10.0, 10.0),
        ('gift', 10.0, 15.0),
        ('heart', 10.0, 10.0),
        ('ring', 10.0, 5.0),
        ('rocket', 10.0, 5.0),
        ('rose', 10.0, 20.0)
    ]
    
    for gift_name, visible, real in gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance) VALUES (?, ?, ?)",
            (gift_name, visible, real)
        )
    
    prices = [
        ('bear', 15),
        ('cake', 50),
        ('cup', 100),
        ('diamond', 100),
        ('flowers', 50),
        ('gift', 25),
        ('heart', 15),
        ('ring', 100),
        ('rocket', 50),
        ('rose', 25)
    ]
    
    for gift_name, price in prices:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_prices (gift_name, price) VALUES (?, ?)",
            (gift_name, price)
        )
    
    conn.commit()
    conn.close()
