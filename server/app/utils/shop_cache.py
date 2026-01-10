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
    Получить подарки с кэшированием в Redis (HASH Structure)
    
    Returns:
        List[Dict]: Список подарков с ценами
    """
    cache_key = "shop:gifts:data"
    
    # 1. Пробуем получить из Redis (HVALS)
    if cache.is_available():
        count = cache.hlen(cache_key)
        if count > 0:
            cached = cache.hvals(cache_key)
            if cached:
                # logger.debug(f"[SHOP_CACHE] ✅ Загружено из Redis HASH: {len(cached)} подарков")
                return cached
    
    # 2. Если кэш пуст - загружаем из БД
    gifts = get_shop_gifts_with_prices()
    
    # 3. Сохраняем в Redis (поштучно в HASH)
    if cache.is_available() and gifts:
        # Используем pipeline или просто цикл (для простоты цикл, так как redis_client wrapper не имеет pipeline)
        # TODO: Add pipeline support to wrapper later for perf
        for gift in gifts:
            slug = gift.get('slug')
            if slug:
                cache.hset(cache_key, slug, gift)
        
        # Ставим TTL на весь хэш
        cache.expire(cache_key, TTL_SHOP_PRICES)
        print(f"[SHOP_CACHE] 💾 Сохранено в Redis HASH: {len(gifts)} подарков (TTL: {TTL_SHOP_PRICES}s)")
    
    return gifts

def update_cached_gift(slug: str, new_amount: int):
    """
    Обновить количество доступных подарков в кэше (без полной инвалидации)
    """
    if not cache.is_available() or not slug:
        return

    cache_key = "shop:gifts:data"
    
    # 1. Получаем текущие данные подарка
    gift_data = cache.hget(cache_key, slug)
    
    if gift_data:
        # 2. Обновляем поле
        gift_data['available_amount'] = new_amount
        
        # 3. Записываем обратно (если amount <= 0, можно было бы удалять, 
        # но лучше оставить с 0 чтобы фильтры работали корректно и не вызывали перефетч)
        cache.hset(cache_key, slug, gift_data)
        # Продлеваем жизнь кэша при активности
        cache.expire(cache_key, TTL_SHOP_PRICES)
        print(f"[SHOP_CACHE] 🔄 Gift {slug} updated in cache (available: {new_amount})")
    else:
        # Если подарка нет в кэше - ничего страшного, при следующем чтении загрузится из БД
        pass

def invalidate_shop_cache():
    """Инвалидировать кэш магазина (вызывается при изменении цен/глобальных настройках)"""
    cache_key = "shop:gifts:data"
    # Legacy key cleanup
    cache.delete("shop:gifts:with_prices") 
    
    if cache.is_available():
        deleted = cache.delete(cache_key)
        print(f"[SHOP_CACHE] 🗑️ Кэш (HASH) инвалидирован: {deleted}")
        return deleted
    return 0
