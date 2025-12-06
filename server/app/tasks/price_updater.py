#!/usr/bin/env python3
"""
Обновление цен LIMITED NFT подарков через Tonnel API
Запускается каждый час
"""
import asyncio
import json
import sqlite3
from datetime import datetime
from curl_cffi.requests import AsyncSession
from app.config import DB_PATH, LOG_BOT_TOKEN, LOGS_ID

async def send_log_to_channel(message):
    """Отправляет сообщение в канал логов"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        return
    
    try:
        from aiogram import Bot
        async with Bot(token=LOG_BOT_TOKEN) as log_bot:
            await log_bot.send_message(LOGS_ID, message, parse_mode="HTML")
    except Exception as e:
        print(f"⚠️  Не удалось отправить лог в канал: {e}")

# Попробуем импортировать fake_useragent, если нет - используем дефолтный UA
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    def get_ua():
        return ua.random
except ImportError:
    def get_ua():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

# Фоны для которых ищем по подарку + фону + модели
SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]

def get_headers():
    """Заголовки как в рабочем скрипте"""
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

async def search_tonnel_resale(gift_name, model=None, backdrop=None, max_retries=3):
    """Поиск подарка на Tonnel маркетплейсе (с обходом Cloudflare через curl_cffi)"""
    
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
        'limit': 1,
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    # Retry логика
    for attempt in range(1, max_retries + 1):
        try:
            # Используем curl_cffi для обхода Cloudflare
            async with AsyncSession(impersonate="chrome") as session:
                response = await session.post(
                    'https://gifts2.tonnel.network/api/pageGifts',
                    json=json_data,
                    headers=get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        if attempt > 1:
                            print(f"   ✅ Успешно на попытке #{attempt}")
                        return data[0].get('price')
                    return None
                elif response.status_code == 403:
                    if attempt < max_retries:
                        wait_time = attempt * 2
                        print(f"   ⚠️  HTTP 403 на попытке #{attempt}/{max_retries}, ожидание {wait_time}с...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print(f"   ❌ HTTP 403 после {max_retries} попыток")
                        return None
                else:
                    print(f"   ⚠️  HTTP {response.status_code} на попытке #{attempt}")
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue
                    return None
                
        except Exception as e:
            if attempt < max_retries:
                print(f"   ⚠️  Ошибка на попытке #{attempt}: {e}")
                await asyncio.sleep(2)
                continue
            else:
                print(f"   ❌ Ошибка после {max_retries} попыток: {e}")
                return None
    
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

async def update_all_prices(send_log=True):
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
            message = "ℹ️ <b>Price Updater</b>\nНет LIMITED NFT подарков для обновления"
            print("ℹ️  Нет LIMITED NFT подарков для обновления")
            await send_log_to_channel(message)
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
                min_ton_price = await search_tonnel_resale(title, model=model, backdrop=backdrop)
            else:
                print(f"   → Поиск по модели...")
                min_ton_price = await search_tonnel_resale(title, model=model)
            
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
            
            # Увеличенная задержка между запросами к разным подаркам
            await asyncio.sleep(5)
        
        print("=" * 80)
        print(f"✅ Обновление завершено")
        print(f"   Обновлено: {updated_count}")
        print(f"   Пропущено: {failed_count}")
        print("=" * 80)
        
        # Отправляем итоговый отчет (только если send_log=True)
        if send_log:
            message = f"✅ <b>Price Updater</b>\n\nОбновлено подарков: <b>{updated_count}</b>"
            if failed_count > 0:
                message += f"\nПропущено: {failed_count}"
            message += f"\n\nВсего обработано: {len(gifts)}"
            await send_log_to_channel(message)
        
        return {"updated": updated_count, "failed": failed_count, "total": len(gifts)}
        
    except Exception as e:
        error_message = f"❌ <b>Price Updater Error</b>\n\n<code>{str(e)}</code>"
        print(f"❌ Критическая ошибка обновления цен: {e}")
        import traceback
        traceback.print_exc()
        await send_log_to_channel(error_message)
        return {"updated": 0, "failed": 0, "total": 0}

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
