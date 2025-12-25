
import sys
import os

# Добавляем текущую директорию в путь, чтобы найти app
sys.path.append(os.getcwd())

try:
    from app.utils.redis_client import cache
    
    if not cache.is_available():
        print("Redis is not available/configured.")
        sys.exit(1)
        
    # Инвалидация кэша магазина
    keys = [
        "shop:gifts:with_prices",
        "shop_prices:*"
    ]
    
    for key in keys:
        if "*" in key:
            cursor = '0'
            while cursor != 0:
                cursor, found_keys = cache.client.scan(cursor=cursor, match=key, count=100)
                if found_keys:
                    cache.client.delete(*found_keys)
                    print(f"Deleted {len(found_keys)} keys matching {key}")
        else:
            cache.client.delete(key)
            print(f"Deleted key: {key}")
            
    print("✅ Shop cache invalidated successfully")
    
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Make sure you are running this from the 'server' directory")
except Exception as e:
    print(f"Error: {e}")
