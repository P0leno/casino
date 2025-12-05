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

async def update_ton_price(silent=False):
    """Обновить цену TON с CoinMarketCap"""
    
    if not COINMARKETCAP_API_KEY:
        if not silent:
            print("⚠️  COINMARKETCAP_API_KEY не установлен в .env")
        return
    
    try:
        import requests
    except ImportError:
        if not silent:
            print("⚠️  requests не установлен")
        return
    
    if not silent:
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
            if not silent:
                print(f"❌ CoinMarketCap API error: HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            return
        
        data = response.json()
        
        if 'data' not in data or '11419' not in data['data']:
            if not silent:
                print(f"❌ Неверный формат ответа от CoinMarketCap")
            return
        
        ton_data = data['data']['11419']
        price_usd = ton_data['quote']['USD']['price']
        
        # Округляем до 4 знаков после запятой
        price_usd = round(price_usd, 4)
        
        if not silent:
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
        
        if not silent:
            print(f"💾 Цена сохранена в БД: {price_usd} USD")
        
    except Exception as e:
        if not silent:
            print(f"❌ Ошибка обновления цены TON: {e}")

async def recalculate_gift_prices(silent=False):
    """
    Инвалидирует кэш цен в Redis
    (Цены пересчитываются динамически при запросе /api/shop/gifts)
    """
    if not silent:
        print("=" * 80)
        print(f"💫 ИНВАЛИДАЦИЯ КЭША ЦЕН - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    try:
        # Инвалидируем кэш цен в Redis
        from app.utils.shop_cache import invalidate_shop_cache
        invalidate_shop_cache()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем количество подарков для отчета
        cursor.execute("SELECT COUNT(*) FROM shop_gifts WHERE ton_price IS NOT NULL AND ton_price > 0")
        result = cursor.fetchone()
        total_gifts = result[0] if result else 0
        conn.close()
        
        if not silent:
            print(f"✅ Кэш инвалидирован для {total_gifts} подарков")
            print("ℹ️  Цены будут пересчитаны автоматически при следующем запросе")
            print("=" * 80)
        
        return {"updated": total_gifts, "total": total_gifts}
        
    except Exception as e:
        if not silent:
            print(f"❌ Ошибка пересчета цен: {e}")
        return {"updated": 0, "total": 0}

async def ton_price_loop():
    """Бесконечный цикл обновления цены TON каждые 5 минут + пересчет цен подарков"""
    # Логируем только при старте, дальше работаем тихо
    print("[TON_PRICE] 🔄 Цикл запущен: обновление курса TON каждые 5 минут (без логов)")
    
    while True:
        try:
            # Задержка перед запуском (при старте уже выполнено одноразово)
            await asyncio.sleep(300)  # 5 минут
            
            # 1. Обновляем цену TON (тихо, без логов)
            await update_ton_price(silent=True)
            
            # 2. Пересчитываем цены подарков (тихо, без логов)
            await recalculate_gift_prices(silent=True)
            
        except Exception as e:
            print(f"[TON_PRICE] ❌ Ошибка в ton_price_loop: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Для тестирования
    asyncio.run(update_ton_price())
