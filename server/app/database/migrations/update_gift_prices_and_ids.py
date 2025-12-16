from app.utils.database import get_db_connection, DB_PATH
#!/usr/bin/env python3
"""
Миграция для обновления gift_id в таблице gift_prices и добавления bottle
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from app.config import DB_PATH

def migrate():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔄 Начинаем миграцию gift_prices...")
    
    # Обновляем gift_id для существующих подарков
    updates = [
        ('5170233102089322756', 'bear'),
        ('5170144170496491616', 'cake'),
        ('5168043875654172773', 'cup'),
        ('5170521118301225164', 'diamond'),
        ('5170314324215857265', 'flowers'),
        ('5170250947678437525', 'gift'),
        ('5170145012310081615', 'heart'),
        ('5170690322832818290', 'ring'),
        ('5170564780938756245', 'rocket'),
        ('5168103777563050263', 'rose'),
    ]
    
    for gift_id, gift_name in updates:
        cursor.execute(
            "UPDATE gift_prices SET gift_id = ? WHERE gift_name = ?",
            (gift_id, gift_name)
        )
        print(f"  ✓ Обновлен {gift_name}: gift_id = {gift_id}")
    
    # Добавляем bottle в gift_chances если его нет
    cursor.execute("SELECT COUNT(*) FROM gift_chances WHERE gift_name = 'bottle'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO gift_chances (gift_name, visible_chance, real_chance, paw_min, paw_max) VALUES (?, ?, ?, ?, ?)",
            ('bottle', 10.0, 10.0, 0, 0)
        )
        print("  ✓ Добавлен bottle в gift_chances")
    
    # Добавляем bottle в gift_prices если его нет
    cursor.execute("SELECT COUNT(*) FROM gift_prices WHERE gift_name = 'bottle'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO gift_prices (gift_name, price, gift_id) VALUES (?, ?, ?)",
            ('bottle', 0, '6028601630662853006')
        )
        print("  ✓ Добавлен bottle в gift_prices (цена: 0)")
    
    conn.commit()
    conn.close()
    
    print("✅ Миграция завершена успешно!")

if __name__ == "__main__":
    migrate()
