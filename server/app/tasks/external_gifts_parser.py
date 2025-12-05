"""
Парсинг всех LIMITED подарков через внешние API (changes.tg + Tonnel)
Используется как дополнение к parse_gifts() для получения подарков которых нет у аккаунта
"""
import asyncio
import aiohttp
import sqlite3
import json
from app.config import DB_PATH

CHANGES_API = "https://api.changes.tg"

async def fetch_all_gift_names():
    """Получает список всех LIMITED подарков из changes.tg"""
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(f"{CHANGES_API}/gifts", timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    gifts = await response.json()
                    print(f"✅ Получено LIMITED подарков из changes.tg: {len(gifts)}")
                    return gifts
                else:
                    print(f"⚠️  Ошибка API changes.tg: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Ошибка получения списка подарков: {e}")
        return []

async def fetch_gift_models(gift_name):
    """Получает список моделей для подарка"""
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            url = f"{CHANGES_API}/models/{gift_name}?sorted"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    models = await response.json()
                    return models
                else:
                    return []
    except Exception as e:
        print(f"⚠️  Ошибка получения моделей для {gift_name}: {e}")
        return []

async def parse_external_gifts():
    """
    Парсит все LIMITED подарки через changes.tg API
    Добавляет в БД только те подарки, которых еще нет
    """
    print("=" * 80)
    print("🌐 ПАРСИНГ LIMITED ПОДАРКОВ ЧЕРЕЗ CHANGES.TG API")
    print("=" * 80)
    
    # 1. Получаем список всех LIMITED подарков
    all_gift_names = await fetch_all_gift_names()
    if not all_gift_names:
        print("⚠️  Не удалось получить список подарков")
        return {"added": 0, "skipped": 0}
    
    # 2. Получаем подарки которые уже есть в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT title FROM shop_gifts WHERE title IS NOT NULL")
    existing_titles = {row[0] for row in cursor.fetchall()}
    
    print(f"📊 Подарков в БД: {len(existing_titles)}")
    
    # 3. Определяем новые подарки
    new_gifts = [g for g in all_gift_names if g not in existing_titles]
    
    if not new_gifts:
        print("✅ Все подарки из changes.tg уже есть в БД")
        conn.close()
        return {"added": 0, "skipped": len(all_gift_names)}
    
    print(f"🆕 Новых подарков для добавления: {len(new_gifts)}")
    print()
    
    added_count = 0
    skipped_count = 0
    
    # 4. Для каждого нового подарка получаем модели и добавляем в БД
    for gift_name in new_gifts[:10]:  # Ограничим первыми 10 для теста
        print(f"🔍 Обработка: {gift_name}")
        
        # Получаем модели
        models = await fetch_gift_models(gift_name)
        if not models:
            print(f"  ⚠️  Модели не найдены")
            skipped_count += 1
            continue
        
        print(f"  📦 Моделей найдено: {len(models)}")
        
        # Берем первую модель для примера
        first_model = models[0]
        model_name = first_model.get("name")
        rarity_model = first_model.get("rarityPermille", 0)
        
        # Формируем путь к анимации
        model_path = f"/gifts/models/{gift_name}/{model_name}.json" if model_name else None
        
        # Вставляем в БД с минимальной информацией
        # gift_id генерируем уникальный (можно использовать hash)
        import hashlib
        gift_id = hashlib.md5(f"{gift_name}_{model_name}".encode()).hexdigest()[:16]
        
        # Slug - используем формат как в Telegram
        slug = f"{gift_name.replace(' ', '')}-{gift_id[:5]}"
        
        try:
            cursor.execute("""
                INSERT INTO shop_gifts 
                (gift_id, slug, title, model_name, model_path, 
                 available_amount, total_amount, price, rarity_model, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, CURRENT_TIMESTAMP)
            """, (
                gift_id, slug, gift_name, model_name, model_path, 
                rarity_model
            ))
            conn.commit()
            print(f"  ✅ Добавлен в БД")
            added_count += 1
        except sqlite3.IntegrityError:
            print(f"  ⏭️  Уже существует")
            skipped_count += 1
            continue
        
        # Задержка между запросами
        await asyncio.sleep(1)
    
    conn.close()
    
    print()
    print("=" * 80)
    print(f"✅ Парсинг завершен: добавлено {added_count}, пропущено {skipped_count}")
    print("=" * 80)
    
    return {"added": added_count, "skipped": skipped_count}

if __name__ == "__main__":
    asyncio.run(parse_external_gifts())
