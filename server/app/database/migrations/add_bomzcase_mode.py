"""
Миграция: Добавление режима bomzcase для платного спина
- Добавляет колонки star_min, star_max в gift_chances
- Добавляет записи для bomzcase режима
"""

import sqlite3
import os

# Путь к базе данных (относительно корня проекта)
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(script_dir, '../../../users.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Начало миграции: add_bomzcase_mode")
    
    # Проверяем существование колонок star_min и star_max
    cursor.execute("PRAGMA table_info(gift_chances)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'star_min' not in columns:
        print("  ➕ Добавление колонки star_min...")
        cursor.execute("ALTER TABLE gift_chances ADD COLUMN star_min INTEGER DEFAULT 1")
        conn.commit()
        print("  ✅ Колонка star_min добавлена")
    else:
        print("  ✓ Колонка star_min уже существует")
    
    if 'star_max' not in columns:
        print("  ➕ Добавление колонки star_max...")
        cursor.execute("ALTER TABLE gift_chances ADD COLUMN star_max INTEGER DEFAULT 5")
        conn.commit()
        print("  ✅ Колонка star_max добавлена")
    else:
        print("  ✓ Колонка star_max уже существует")
    
    # Добавляем записи для bomzcase
    bomzcase_gifts = [
        ('bear', 15.0, 15.0, 0, 0, 1, 5),
        ('heart', 15.0, 15.0, 0, 0, 1, 5),
        ('rose', 15.0, 15.0, 0, 0, 1, 5),
        ('gift', 15.0, 15.0, 0, 0, 1, 5),
        ('paw', 20.0, 20.0, 1, 10, 1, 5),
        ('star', 20.0, 20.0, 0, 0, 1, 5)
    ]
    
    print("  ➕ Добавление bomzcase подарков...")
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in bomzcase_gifts:
        cursor.execute(
            "INSERT OR REPLACE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'bomzcase', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
        print(f"    ✓ {gift_name}")
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM gift_chances WHERE mode = 'bomzcase'")
    count = cursor.fetchone()[0]
    print(f"\n  📊 Всего bomzcase подарков: {count}")
    
    conn.close()
    print("\n✅ Миграция завершена успешно!")

if __name__ == "__main__":
    migrate()
