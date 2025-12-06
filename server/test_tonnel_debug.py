#!/usr/bin/env python3
"""
Тестовый скрипт для отладки парсинга цен через Tonnel API
Использует pyrogram для получения подарков
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv
import aiohttp

# Загружаем .env
load_dotenv()

# Добавляем путь к app
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from pyrogram import Client

# Pyrogram credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "gift_sender_session"  # Используем рабочую сессию

# Fake user agent
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    def get_ua():
        return ua.random
except ImportError:
    def get_ua():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

def get_headers():
    """Заголовки для Tonnel API"""
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

async def search_tonnel_resale(gift_name, model=None):
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
    if model:
        filter_data["model"] = {"$regex": f"^{model} \\("}
    
    sort_data = {
        'price': 1,  # Сортировка по цене (от дешевых)
        'message_post_time': -1
    }
    
    json_data = {
        'page': 1,
        'limit': 10,  # Берем 10 для отладки
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    print(f"\n   📤 Отправка запроса к Tonnel API...")
    print(f"   Filter: {json.dumps(filter_data, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://gifts2.tonnel.network/api/pageGifts',
                json=json_data,
                headers=get_headers(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                print(f"   📥 Статус: {response.status}")
                print(f"   📋 Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Успешно! Получено объектов: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                else:
                    text = await response.text()
                    print(f"   ❌ Ошибка {response.status}")
                    print(f"   Response: {text[:200]}")
                    return None
                    
    except Exception as e:
        print(f"   💥 Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

async def parse_gifts_from_telegram():
    """Парсинг подарков через Pyrogram"""
    print("=" * 80)
    print("🚀 ТЕСТОВЫЙ СКРИПТ - ПАРСИНГ ПОДАРКОВ + TONNEL API")
    print("=" * 80)
    print()
    
    if not API_ID or not API_HASH:
        print("❌ Ошибка: API_ID или API_HASH не найдены в .env")
        return
    
    print(f"📱 Pyrogram: API_ID={API_ID}, SESSION={SESSION_NAME}")
    print()
    
    # Создаем клиент Pyrogram
    app = Client(
        name=SESSION_NAME,
        api_id=int(API_ID),
        api_hash=API_HASH,
        workdir="sessions"
    )
    
    try:
        print("🔌 Подключение к Telegram...")
        await app.start()
        print("✅ Подключено!")
        print()
        
        # Получаем свой ID
        me = await app.get_me()
        print(f"👤 Аккаунт: {me.first_name} (@{me.username or 'no username'})")
        print()
        
        # Парсим подарки
        print("🎁 Парсинг подарков через get_chat_gifts()...")
        gifts = await app.get_chat_gifts(chat_id=me.id, exclude_unlimited=True)
        
        print(f"✅ Получено LIMITED подарков: {len(gifts)}")
        print()
        
        if not gifts:
            print("⚠️  Нет LIMITED подарков на аккаунте")
            return
        
        # Обрабатываем каждый подарок
        for i, gift in enumerate(gifts[:3], 1):  # Первые 3 для теста
            print("=" * 80)
            print(f"🎁 Подарок #{i}: {gift.title}")
            print("=" * 80)
            
            # Основная информация
            print(f"   ID: {gift.id}")
            print(f"   Slug: {gift.slug}")
            print(f"   Total: {gift.total_count}")
            print(f"   Available: {gift.available_count}")
            
            # Transfer price (LIMITED NFT признак)
            if hasattr(gift, 'transfer_price') and gift.transfer_price:
                print(f"   💰 Transfer Price: {gift.transfer_price} ⭐")
            else:
                print(f"   ⚠️  Transfer Price: None (не LIMITED?)")
                continue
            
            # Attributes для модели
            model_name = None
            backdrop_name = None
            
            if hasattr(gift, 'attributes') and gift.attributes:
                print(f"\n   📊 Атрибуты ({len(gift.attributes)} шт):")
                for attr in gift.attributes:
                    attr_name = attr.name if hasattr(attr, 'name') else 'unknown'
                    print(f"      - {attr_name}")
                    
                    # Ищем MODEL
                    if attr_name == "MODEL":
                        if hasattr(attr, 'document') and attr.document:
                            doc = attr.document
                            if hasattr(doc, 'file_name'):
                                # "Giant Crab.tgs" -> "Giant Crab"
                                model_name = doc.file_name.replace('.tgs', '')
                                print(f"        ✅ Model: {model_name}")
                    
                    # Ищем BACKDROP
                    elif attr_name == "BACKDROP":
                        if hasattr(attr, 'document') and attr.document:
                            doc = attr.document
                            if hasattr(doc, 'file_name'):
                                # "Red (1).tgs" -> "Red"
                                backdrop_name = doc.file_name.replace('.tgs', '').split('(')[0].strip()
                                print(f"        ✅ Backdrop: {backdrop_name}")
            
            # Поиск на Tonnel
            print(f"\n   🔍 Поиск на Tonnel маркетплейсе...")
            if model_name:
                print(f"   Модель: {model_name}")
                result = await search_tonnel_resale(gift.title, model=model_name)
                
                if result and isinstance(result, list) and len(result) > 0:
                    print(f"\n   ✅ НАЙДЕНО на ресейле: {len(result)} предложений")
                    
                    # Показываем первые 3
                    for j, resale in enumerate(result[:3], 1):
                        price = resale.get('price', 'N/A')
                        model = resale.get('model', 'N/A')
                        backdrop = resale.get('backdrop', 'N/A')
                        gift_num = resale.get('gift_num', 'N/A')
                        
                        print(f"\n      #{j}:")
                        print(f"         💰 Цена: {price} TON")
                        print(f"         🎨 Модель: {model}")
                        print(f"         🖼️  Фон: {backdrop}")
                        print(f"         #️⃣  Номер: #{gift_num}")
                    
                    # Минимальная цена
                    min_price = result[0].get('price')
                    print(f"\n   💎 Минимальная цена: {min_price} TON")
                    
                elif result is None:
                    print(f"   ❌ Ошибка при запросе к Tonnel")
                else:
                    print(f"   ℹ️  На ресейле нет предложений")
            else:
                print(f"   ⚠️  Модель не найдена в атрибутах, пропускаем")
            
            print()
        
        print("=" * 80)
        print("✅ ТЕСТ ЗАВЕРШЕН")
        print("=" * 80)
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🔌 Отключение от Telegram...")
        try:
            if app.is_connected:
                await app.stop()
                print("✅ Отключено")
            else:
                print("ℹ️  Клиент уже отключен")
        except Exception as e:
            print(f"⚠️  Ошибка при отключении: {e}")

if __name__ == "__main__":
    asyncio.run(parse_gifts_from_telegram())
