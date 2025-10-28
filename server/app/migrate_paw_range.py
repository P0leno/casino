import sqlite3
from config import DB_PATH

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(gift_chances)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        has_paw_amount = 'paw_amount' in columns
        has_paw_min = 'paw_min' in columns
        has_paw_max = 'paw_max' in columns
        
        if has_paw_amount and not has_paw_min and not has_paw_max:
            print("Migrating from paw_amount to paw_min/paw_max...")
            
            # Добавляем новые колонки
            cursor.execute("ALTER TABLE gift_chances ADD COLUMN paw_min INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE gift_chances ADD COLUMN paw_max INTEGER DEFAULT 0")
            
            # Переносим данные: если был paw_amount=5, делаем paw_min=1, paw_max=5
            cursor.execute("SELECT gift_name, paw_amount FROM gift_chances WHERE paw_amount > 0")
            results = cursor.fetchall()
            
            for gift_name, paw_amount in results:
                cursor.execute(
                    "UPDATE gift_chances SET paw_min = 1, paw_max = ? WHERE gift_name = ?",
                    (paw_amount, gift_name)
                )
            
            conn.commit()
            print(f"✓ Migrated {len(results)} gifts with paw rewards")
            
            # Удаляем старую колонку (SQLite не поддерживает DROP COLUMN напрямую)
            print("Note: Old paw_amount column will remain but not be used")
            
        elif not has_paw_min and not has_paw_max:
            print("Adding paw_min and paw_max columns...")
            cursor.execute("ALTER TABLE gift_chances ADD COLUMN paw_min INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE gift_chances ADD COLUMN paw_max INTEGER DEFAULT 0")
            
            # Устанавливаем 1-5 для paw если он существует
            cursor.execute("SELECT gift_name FROM gift_chances WHERE gift_name = 'paw'")
            if cursor.fetchone():
                cursor.execute("UPDATE gift_chances SET paw_min = 1, paw_max = 5 WHERE gift_name = 'paw'")
                print("✓ Set paw range to 1-5")
            
            conn.commit()
            print("✓ Columns added successfully")
        else:
            print("✓ paw_min and paw_max already exist")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
