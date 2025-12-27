import json
from app.utils.database import get_db_connection
from app.utils.shop_cache import invalidate_shop_cache

def sync_shop_amounts():
    """
    Синхронизирует available_amount в таблице shop_gifts
    на основе реального количества подарков на руках у пользователей.
    available = total - owned
    """
    try:
        print("[SHOP_SYNC] 🔄 Начало синхронизации количества подарков...")
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Получаем все NFT подарки из магазина
        cursor.execute("SELECT slug, total_amount, title FROM shop_gifts")
        shop_gifts = cursor.fetchall()  # [(slug, total, title), ...]
        
        shop_stats = {row[0]: {'total': row[1], 'title': row[2], 'owned': 0} for row in shop_gifts}
        
        if not shop_stats:
            print("[SHOP_SYNC] ⚠️ Нет подарков в магазине shop_gifts")
            conn.close()
            return

        # 2. Считаем подарки на руках у пользователей (эффективный проход)
        # Для оптимизации можно использовать json_each, но для совместимости парсим в Python
        cursor.execute("SELECT inventory FROM users")
        
        user_count = 0
        nft_count = 0
        
        while True:
            # Читаем чанками по 1000 пользователей
            rows = cursor.fetchmany(1000)
            if not rows:
                break
                
            for row in rows:
                inventory_json = row[0]
                user_count += 1
                if not inventory_json or inventory_json == '[]':
                    continue
                    
                try:
                    inventory = json.loads(inventory_json)
                    # inventory - список slug'ов
                    for item in inventory:
                        if item in shop_stats:
                            # Учитываем только те, что есть в магазине
                            shop_stats[item]['owned'] += 1
                            nft_count += 1
                except:
                    continue

        # 3. Обновляем available_amount
        updates = []
        for slug, stats in shop_stats.items():
            expected_available = stats['total'] - stats['owned']
            # Защита от отрицательных значений
            if expected_available < 0:
                print(f"[SHOP_SYNC] ⚠️ Gift '{stats['title']}' has negative availability! Total: {stats['total']}, Owned: {stats['owned']}")
                expected_available = 0
            
            updates.append((expected_available, slug))
            # print(f"[SHOP_SYNC] Gift '{stats['title']}': Available {expected_available} (Total {stats['total']} - Owned {stats['owned']})")

        # 4. Применяем обновления
        if updates:
            cursor.executemany("UPDATE shop_gifts SET available_amount = ? WHERE slug = ?", updates)
            conn.commit()
            print(f"[SHOP_SYNC] ✅ Обновлено {len(updates)} подарков. Всего найдено {nft_count} NFT у {user_count} пользователей.")
            
            # Инвалидируем кэш после обновления
            invalidate_shop_cache()
        
        conn.close()

    except Exception as e:
        print(f"[SHOP_SYNC] ❌ Ошибка синхронизации: {e}")
