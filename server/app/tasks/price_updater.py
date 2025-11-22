#!/usr/bin/env python3
"""
Обновление цен LIMITED NFT подарков через Tonnel API
Запускается каждый час
"""
import asyncio
import json
import sqlite3
from datetime import datetime
from app.config import DB_PATH

# Фоны для которых ищем по подарку + фону + модели
SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]

def get_headers():
    return {
        "authority": "gifts2.tonnel.network",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://market.tonnel.network",
        "priority": "u=1, i",
        "referer": "https://market.tonnel.network/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

def search_tonnel_resale(gift_name, model=None, backdrop=None):
    """Поиск подарка на Tonnel маркетплейсе"""
    try:
        from curl_cffi import requests
    except ImportError:
        import requests
    
    # Базовый фильтр
    filter_data = {
        "price": {"$exists": True},
        "refunded": {"$ne": True},
        "buyer": {"$exists": False},
        "export_at": {"$exists": True},
        "gift_name": gift_name,
        "asset": "TON"
    }
    
    # Если фон специальный - ищем по фону + модели
    if backdrop and backdrop in SPECIAL_BACKDROPS and model:
        filter_data["backdrop"] = {"$regex": f"^{backdrop} \\("}
        filter_data["model"] = {"$regex": f"^{model} \\("}
    # Иначе только по модели
    elif model:
        filter_data["model"] = {"$regex": f"^{model} \\("}
    
    sort_data = {
        'price': 1,  # Сортировка по цене (от дешевых)
        'message_post_time': -1
    }
    
    json_data = {
        'page': 1,
        'limit': 1,  # Нужна только минимальная цена
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    try:
        # Пытаемся использовать curl_cffi
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.post(
                'https://gifts2.tonnel.network/api/pageGifts',
                json=json_data,
                headers=get_headers(),
                impersonate="chrome",
                timeout=10
            )
        except ImportError:
            # Fallback на обычный requests
            response = requests.post(
                'https://gifts2.tonnel.network/api/pageGifts',
                json=json_data,
                headers=get_headers(),
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('price')
            return None
        else:
            print(f"⚠️  Tonnel API error: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️  Error fetching from Tonnel: {e}")
        return None

def update_gift_ton_price(gift_id, ton_price):
    """Обновить цену подарка в TON (с Tonnel)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE shop_gifts 
            SET ton_price = ?, price_update = CURRENT_TIMESTAMP 
            WHERE gift_id = ?
        """, (ton_price, gift_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error updating TON price for {gift_id}: {e}")
        return False

async def update_all_prices():
    """Обновить цены в TON с Tonnel маркетплейса"""
    print("=" * 80)
    print(f"🔄 ОБНОВЛЕНИЕ ЦЕН С TONNEL МАРКЕТПЛЕЙСА - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем все LIMITED NFT (у них есть slug и модель)
        cursor.execute("""
            SELECT gift_id, title, model_name, backdrop_name, ton_price, price_update
            FROM shop_gifts
            WHERE slug IS NOT NULL AND slug != '' 
              AND model_name IS NOT NULL AND model_name != ''
            ORDER BY title
        """)
        
        gifts = cursor.fetchall()
        conn.close()
        
        if not gifts:
            print("ℹ️  Нет LIMITED NFT подарков для обновления")
            return
        
        print(f"📦 Найдено подарков: {len(gifts)}")
        print()
        
        updated_count = 0
        failed_count = 0
        
        for gift_id, title, model, backdrop, current_ton_price, last_update in gifts:
            print(f"🔍 {title}")
            print(f"   Модель: {model or 'N/A'}")
            print(f"   Фон: {backdrop or 'N/A'}")
            print(f"   Текущая цена: {current_ton_price} TON" if current_ton_price else "   Текущая цена: Не установлена")
            print(f"   Последнее обновление: {last_update or 'Никогда'}")
            
            # Определяем по чему искать
            search_by_backdrop = backdrop and backdrop in SPECIAL_BACKDROPS
            
            if search_by_backdrop:
                print(f"   → Поиск по фону + модели...")
                min_ton_price = search_tonnel_resale(title, model=model, backdrop=backdrop)
            else:
                print(f"   → Поиск по модели...")
                min_ton_price = search_tonnel_resale(title, model=model)
            
            if min_ton_price is not None:
                print(f"   ✅ Найдена минимальная цена: {min_ton_price} TON")
                
                # Проверяем изменилась ли цена
                price_changed = (current_ton_price is None or 
                               abs(min_ton_price - current_ton_price) > 0.01)
                
                if price_changed:
                    if update_gift_ton_price(gift_id, min_ton_price):
                        if current_ton_price:
                            print(f"   💾 Цена в TON обновлена: {current_ton_price} → {min_ton_price}")
                        else:
                            print(f"   💾 Цена в TON установлена: {min_ton_price}")
                        updated_count += 1
                    else:
                        print(f"   ❌ Не удалось обновить цену")
                        failed_count += 1
                else:
                    print(f"   ℹ️  Цена в TON не изменилась")
            else:
                print(f"   ⚠️  Не найдено предложений на ресейле")
                failed_count += 1
            
            print()
            
            # Задержка между запросами
            await asyncio.sleep(2)
        
        print("=" * 80)
        print(f"✅ Обновление завершено")
        print(f"   Обновлено: {updated_count}")
        print(f"   Пропущено: {failed_count}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Критическая ошибка обновления цен: {e}")

async def price_update_loop():
    """Бесконечный цикл обновления цен каждый час"""
    while True:
        try:
            # Небольшая задержка перед первым запуском (чтобы не конфликтовать с первоначальной загрузкой)
            await asyncio.sleep(3600)  # 1 час
            
            await update_all_prices()
        except Exception as e:
            print(f"❌ Ошибка в price_update_loop: {e}")
        
        # Следующее обновление - еще через час
        print(f"⏳ Следующее обновление цен с Tonnel через 1 час...")

if __name__ == "__main__":
    # Для тестирования
    asyncio.run(update_all_prices())
