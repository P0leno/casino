
import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = "users.db"

def fix_shop_amounts():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting shop consistency check...")

        # 1. Получаем все NFT подарки из магазина
        cursor.execute("SELECT slug, total_amount, title FROM shop_gifts")
        shop_gifts = cursor.fetchall()  # [(slug, total, title), ...]
        
        shop_stats = {row[0]: {'total': row[1], 'title': row[2], 'owned': 0} for row in shop_gifts}
        print(f"Found {len(shop_stats)} NFT gifts in shop.")

        # 2. Считаем подарки на руках у пользователей
        cursor.execute("SELECT id, inventory FROM users")
        
        user_count = 0
        nft_count = 0
        
        for user_id, inventory_json in cursor.fetchall():
            user_count += 1
            if not inventory_json:
                continue
                
            try:
                inventory = json.loads(inventory_json)
                # inventory - это список строк (slugs)
                for item in inventory:
                    if item in shop_stats:
                        shop_stats[item]['owned'] += 1
                        nft_count += 1
            except json.JSONDecodeError:
                print(f"Error decoding inventory for user {user_id}")
                continue

        print(f"Scanned {user_count} users. Found {nft_count} owned NFTs.")

        # 3. Обновляем available_amount
        updates = []
        for slug, stats in shop_stats.items():
            expected_available = stats['total'] - stats['owned']
            # Защита от отрицательных значений (если вдруг total уменьшили, а подарки остались)
            if expected_available < 0:
                print(f"WARNING: Gift '{stats['title']}' ({slug}) has negative availability! Total: {stats['total']}, Owned: {stats['owned']}")
                expected_available = 0
            
            updates.append((expected_available, slug))
            print(f"Gift '{stats['title']}': Total {stats['total']} - Owned {stats['owned']} = Available {expected_available}")

        # 4. Применяем обновления
        cursor.executemany("UPDATE shop_gifts SET available_amount = ? WHERE slug = ?", updates)
        conn.commit()
        print("Successfully updated shop_gifts table.")
        
        # 5. Сбрасываем кэш Redis (если есть, но тут простой скрипт)
        print("NOTE: Don't forget to clear Redis cache via admin panel or restart server if using cache.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_shop_amounts()
