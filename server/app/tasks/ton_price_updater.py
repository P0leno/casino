#!/usr/bin/env python3
"""
Обновление цены TON в USD с CoinMarketCap
Запускается каждые 15 минут
"""
import asyncio
import sqlite3
from datetime import datetime
from app.config import DB_PATH
import os

COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', '')

async def update_ton_price():
    """Обновить цену TON с CoinMarketCap"""
    
    if not COINMARKETCAP_API_KEY:
        print("⚠️  COINMARKETCAP_API_KEY не установлен в .env")
        return
    
    try:
        import requests
    except ImportError:
        print("⚠️  requests не установлен")
        return
    
    print(f"🔄 Обновление цены TON - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # CoinMarketCap API - TON ID = 11419
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        
        headers = {
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'id': '11419',  # TON ID в CoinMarketCap
            'convert': 'USD'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ CoinMarketCap API error: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return
        
        data = response.json()
        
        if 'data' not in data or '11419' not in data['data']:
            print(f"❌ Неверный формат ответа от CoinMarketCap")
            return
        
        ton_data = data['data']['11419']
        price_usd = ton_data['quote']['USD']['price']
        
        # Округляем до 4 знаков после запятой
        price_usd = round(price_usd, 4)
        
        print(f"✅ Цена TON: ${price_usd}")
        
        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE settings 
            SET value = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE key = 'ton_price_usd'
        """, (str(price_usd),))
        
        if cursor.rowcount == 0:
            # Если настройка не существует - создаем
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES ('ton_price_usd', ?, 'Цена TON в USD (CoinMarketCap)')
            """, (str(price_usd),))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Цена сохранена в БД: {price_usd} USD")
        
    except Exception as e:
        print(f"❌ Ошибка обновления цены TON: {e}")

async def recalculate_gift_prices():
    """Пересчитать цены подарков в звездах используя актуальную цену TON"""
    print("=" * 80)
    print(f"💫 ПЕРЕСЧЕТ ЦЕН ПОДАРКОВ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем цену TON в USD
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        ton_price_result = cursor.fetchone()
        
        if not ton_price_result:
            print("⚠️  Цена TON не найдена в настройках")
            conn.close()
            return
        
        # Получаем комиссию магазина
        cursor.execute("SELECT value FROM settings WHERE key = 'shop_commission'")
        commission_result = cursor.fetchone()
        commission_percent = float(commission_result[0]) if commission_result else 10.0
        
        ton_price_usd = float(ton_price_result[0])
        print(f"💵 Цена TON: ${ton_price_usd}")
        print(f"⭐ Курс: 50 звезд = $0.75")
        print(f"💰 Наценка: {commission_percent}%")
        print()
        
        # Получаем все подарки с установленной ценой в TON
        cursor.execute("""
            SELECT gift_id, title, ton_price, price
            FROM shop_gifts
            WHERE ton_price IS NOT NULL AND ton_price > 0
        """)
        
        gifts = cursor.fetchall()
        
        if not gifts:
            print("ℹ️  Нет подарков с установленной ценой в TON")
            conn.close()
            return
        
        print(f"📦 Найдено подарков: {len(gifts)}")
        print()
        
        updated_count = 0
        
        for gift_id, title, ton_price, current_stars_price in gifts:
            # Конвертируем TON в USD
            price_usd = ton_price * ton_price_usd
            
            # Конвертируем USD в звезды: 50 звезд = 0.75 USD
            stars_price = (price_usd / 0.75) * 50
            
            # Добавляем комиссию магазина
            stars_price = stars_price * (1 + commission_percent / 100)
            
            # Округляем вверх до целого
            import math
            stars_price = math.ceil(stars_price)
            
            # Обновляем если цена изменилась
            if stars_price != current_stars_price:
                cursor.execute("""
                    UPDATE shop_gifts 
                    SET price = ? 
                    WHERE gift_id = ?
                """, (stars_price, gift_id))
                
                print(f"✅ {title}: {ton_price} TON = ${price_usd:.2f} = {stars_price}⭐ (было: {current_stars_price}⭐)")
                updated_count += 1
        
        conn.commit()
        conn.close()
        
        print()
        print(f"✅ Пересчет завершен: обновлено {updated_count} подарков")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Ошибка пересчета цен: {e}")

async def ton_price_loop():
    """Бесконечный цикл обновления цены TON каждые 5 минут + пересчет цен подарков"""
    while True:
        try:
            # Задержка перед запуском (при старте уже выполнено одноразово)
            await asyncio.sleep(300)  # 5 минут
            
            # 1. Обновляем цену TON
            await update_ton_price()
            
            # 2. Пересчитываем цены подарков
            await recalculate_gift_prices()
            
        except Exception as e:
            print(f"❌ Ошибка в ton_price_loop: {e}")
        
        # Следующее обновление
        print(f"⏳ Следующее обновление курса TON через 5 минут...")

if __name__ == "__main__":
    # Для тестирования
    asyncio.run(update_ton_price())
