#!/usr/bin/env python3
"""
Поиск LIMITED NFT подарков на ресейле через Tonnel API
"""
import json
import sqlite3
from curl_cffi import requests

# Попробуем импортировать fake_useragent, если нет - используем дефолтный UA
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    def get_ua():
        return ua.random
except ImportError:
    def get_ua():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

# Конфигурация
DB_PATH = "users.db"

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
        "user-agent": get_ua()
    }

def get_shop_gifts():
    """Получить LIMITED NFT подарки из БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT gift_id, title, slug, price, total_amount, available_amount, model_name
        FROM shop_gifts
        WHERE price > 0
        ORDER BY price DESC
        LIMIT 10
    """)
    
    gifts = []
    for row in cursor.fetchall():
        gifts.append({
            'gift_id': row[0],
            'name': row[1],
            'slug': row[2],
            'price': row[3],
            'total': row[4],
            'available': row[5],
            'model': row[6]
        })
    
    conn.close()
    return gifts

def search_tonnel_resale(gift_name, model=None):
    """Поиск подарка на Tonnel маркетплейсе"""
    
    # Базовый фильтр
    filter_data = {
        "price": {"$exists": True},
        "refunded": {"$ne": True},
        "buyer": {"$exists": False},
        "export_at": {"$exists": True},
        "gift_name": gift_name,
        "asset": "TON"
    }
    
    # Добавляем фильтр по модели если указан
    # Используем regex т.к. в API модель с процентом: "Giant Crab (1.5%)"
    if model:
        filter_data["model"] = {"$regex": f"^{model} \\("}  # Ищем "Giant Crab ("
    
    sort_data = {
        'price': 1,  # Сортировка по цене (от дешевых)
        'message_post_time': -1
    }
    
    json_data = {
        'page': 1,
        'limit': 10,
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    try:
        response = requests.post(
            'https://gifts2.tonnel.network/api/pageGifts',
            json=json_data,
            headers=get_headers(),
            impersonate="chrome",  # Имитируем Chrome браузер
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Показываем текст ответа для отладки
            return {'error': f'HTTP {response.status_code}', 'response_text': response.text[:200]}
            
    except Exception as e:
        return {'error': str(e)}

def main():
    print("=" * 80)
    print("ПОИСК LIMITED NFT НА TONNEL МАРКЕТПЛЕЙСЕ")
    print("=" * 80)
    print()
    
    # Получаем подарки из БД
    print("📦 Загрузка LIMITED NFT из БД...")
    gifts = get_shop_gifts()
    print(f"✅ Найдено: {len(gifts)} подарков\n")
    
    if not gifts:
        print("⚠️  Нет LIMITED NFT в базе данных")
        return
    
    # Поиск каждого подарка
    for i, gift in enumerate(gifts, 1):
        print(f"{i}. {gift['name']}")
        print(f"   Gift ID: {gift['gift_id']}")
        print(f"   Slug: {gift['slug']}")
        print(f"   Model: {gift['model']}")
        print(f"   💰 Цена передачи: {gift['price']}⭐")
        print(f"   📦 Доступно: {gift['available']}/{gift['total']}")
        print()
        
        print(f"   🔍 Поиск на Tonnel маркетплейсе (фильтр: {gift['model']})...")
        result = search_tonnel_resale(gift['name'], model=gift['model'])
        
        # Обработка ответа
        if isinstance(result, dict) and 'error' in result:
            print(f"   ❌ Ошибка: {result['error']}")
            if 'response_text' in result:
                print(f"   Response: {result['response_text']}")
        elif isinstance(result, list) and len(result) > 0:
            # API вернул список подарков
            print(f"   ✅ НАЙДЕНО НА РЕСЕЙЛЕ: {len(result)} предложений")
            print()
            
            # Показываем первые 5
            for j, resale in enumerate(result[:5], 1):
                print(f"      #{j} Предложение:")
                print(f"         Цена: {resale.get('price', 'N/A')} {resale.get('asset', 'TON')}")
                print(f"         Модель: {resale.get('model', 'N/A')}")
                print(f"         Символ: {resale.get('symbol', 'N/A')}")
                print(f"         Фон: {resale.get('backdrop', 'N/A')}")
                print(f"         Номер: #{resale.get('gift_num', 'N/A')}")
                print(f"         Владелец: {resale.get('owner', 'N/A')}")
                
                # Можно экспортировать с
                export_at = resale.get('export_at')
                if export_at:
                    print(f"         Экспорт доступен: {export_at}")
                
                print()
            
            if len(result) > 5:
                print(f"      ... и еще {len(result) - 5} предложений")
                print()
        elif isinstance(result, dict) and 'data' in result and result['data']:
            # Старый формат ответа
            gifts_data = result['data']
            total = result.get('total', 0)
            
            print(f"   ✅ НАЙДЕНО НА РЕСЕЙЛЕ: {total} предложений")
            print()
            
            for j, resale in enumerate(gifts_data[:5], 1):
                print(f"      #{j} Предложение:")
                print(f"         Цена: {resale.get('price', 'N/A')} {resale.get('asset', 'TON')}")
                print(f"         Модель: {resale.get('model', 'N/A')}")
                print(f"         Символ: {resale.get('symbol', 'N/A')}")
                print(f"         Фон: {resale.get('backdrop', 'N/A')}")
                print(f"         Номер: #{resale.get('gift_num', 'N/A')}")
                print()
        else:
            print(f"   ℹ️  На ресейле нет предложений")
        
        print("-" * 80)
        print()

if __name__ == "__main__":
    main()
