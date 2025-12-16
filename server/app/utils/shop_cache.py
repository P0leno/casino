"""
Кэширование цен магазина в Redis
SQLite: ton_price (обновляется парсером)
Redis: stars_price (пересчитывается динамически)
"""
import math
from typing import Optional, List, Dict
from app.utils.redis_client import cache
from app.utils.database import get_db_connection

TTL_SHOP_PRICES = 300  # 5 минут кэш для цен в звездах

def get_ton_price_usd() -> float:
    """Получить текущую цену TON в USD"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return float(result[0])
        return 0.0
    except Exception as e:
        print(f"[SHOP_CACHE] Ошибка получения курса TON: {e}")
        return 0.0

def get_shop_commission() -> float:
    """Получить комиссию магазина"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'shop_commission'")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return float(result[0])
        return 10.0  # По умолчанию 10%
    except Exception as e:
        print(f"[SHOP_CACHE] Ошибка получения комиссии: {e}")
        return 10.0

def calculate_stars_price(ton_price: float, ton_usd: float, commission: float) -> int:
    """
    Пересчитать цену из TON в звезды
    
    Args:
        ton_price: Цена в TON
        ton_usd: Курс TON в USD
        commission: Комиссия магазина в процентах
    
    Returns:
        Цена в звездах (int)
    """
    if not ton_price or ton_price <= 0:
        return 0
    
    # TON -> USD
    price_usd = ton_price * ton_usd
    
    # USD -> Stars (50 звезд = 0.75 USD)
    stars_price = (price_usd / 0.75) * 50
    
    # Добавляем комиссию
    stars_price = stars_price * (1 + commission / 100)
    
    # Округляем вверх
    return math.ceil(stars_price)

def get_shop_gifts_with_prices() -> List[Dict]:
    """
    Получить все подарки с пересчитанными ценами в звездах
    
    Returns:
        List[Dict]: Список подарков с полями:
            - gift_id, slug, title, model_name, backdrop_name
            - ton_price (из SQLite)
            - price (stars_price, пересчитанная динамически)
    """
    try:
        # Получаем курс и комиссию
        ton_usd = get_ton_price_usd()
        commission = get_shop_commission()
        
        if ton_usd <= 0:
            print("[SHOP_CACHE] ⚠️ Курс TON не установлен, используем цены по умолчанию")
        
        # Получаем подарки из SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT gift_id, slug, title, model_name, model_path, 
                   symbol_name, backdrop_name, center_color, edge_color, 
                   ton_price, available_amount, total_amount,
                   rarity_model, rarity_symbol, rarity_backdrop
            FROM shop_gifts
            WHERE ton_price IS NOT NULL AND ton_price > 0
            ORDER BY title
        """)
        
        gifts = []
        for row in cursor.fetchall():
            gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name, \
            center_color, edge_color, ton_price, available_amount, total_amount, \
            rarity_model, rarity_symbol, rarity_backdrop = row
            
            # Пересчитываем цену в звезды
            stars_price = calculate_stars_price(ton_price, ton_usd, commission)
            
            gifts.append({
                "gift_id": gift_id,
                "slug": slug,
                "title": title,
                "model_name": model_name,
                "model_path": model_path,
                "symbol_name": symbol_name,
                "backdrop_name": backdrop_name,
                "center_color": center_color,
                "edge_color": edge_color,
                "ton_price": ton_price,
                "price": stars_price,  # Цена в звездах
                "available_amount": available_amount or 0,
                "total_amount": total_amount or 0,
                "rarity_model": rarity_model,
                "rarity_symbol": rarity_symbol,
                "rarity_backdrop": rarity_backdrop
            })
        
        conn.close()
        print(f"[SHOP_CACHE] Загружено {len(gifts)} подарков из БД")
        return gifts
        
    except Exception as e:
        print(f"[SHOP_CACHE] Ошибка загрузки подарков: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_cached_shop_gifts() -> List[Dict]:
    """
    Получить подарки с кэшированием в Redis
    
    Returns:
        List[Dict]: Список подарков с ценами
    """
    cache_key = "shop:gifts:with_prices"
    
    # Пробуем получить из Redis
    if cache.is_available():
        cached = cache.get(cache_key)
        if cached:
            print(f"[SHOP_CACHE] ✅ Загружено из Redis: {len(cached)} подарков")
            return cached
    
    # Если нет в кэше - загружаем из БД
    gifts = get_shop_gifts_with_prices()
    
    # Сохраняем в Redis
    if cache.is_available() and gifts:
        cache.set(cache_key, gifts, TTL_SHOP_PRICES)
        print(f"[SHOP_CACHE] 💾 Сохранено в Redis: {len(gifts)} подарков (TTL: {TTL_SHOP_PRICES}s)")
    
    return gifts

def invalidate_shop_cache():
    """Инвалидировать кэш магазина (вызывается при обновлении цен)"""
    cache_key = "shop:gifts:with_prices"
    if cache.is_available():
        deleted = cache.delete(cache_key)
        print(f"[SHOP_CACHE] 🗑️ Кэш инвалидирован: {deleted}")
        return deleted
    return 0
