#!/usr/bin/env python3
"""
Миграция: создание таблицы settings для системных настроек
"""
import sqlite3
import sys
import os

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.config import DB_PATH

def create_settings_table():
    """Создание таблицы settings"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Создаём таблицу settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Вставляем дефолтные настройки
    default_settings = [
        ('stars_topup_enabled', 'true', 'Пополнение звездами'),
        ('max_crash_multiplier', '10.0', 'Максимальный коэффициент краша'),
    ]
    
    for key, value, description in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        """, (key, value, description))
    
    conn.commit()
    conn.close()
    print("✅ Таблица settings создана и заполнена дефолтными значениями")

if __name__ == "__main__":
    create_settings_table()
