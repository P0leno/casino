"""
Redis Client с connection pooling и fallback на SQLite
"""
import redis
from redis.connection import ConnectionPool
import json
import os
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

# Конфигурация из .env
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

# Connection pool (переиспользование соединений)
pool = ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    max_connections=REDIS_MAX_CONNECTIONS,
    socket_timeout=REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
    decode_responses=True  # Автоматически декодировать в строки
)

redis_client = redis.Redis(connection_pool=pool)

# Проверка подключения при старте
try:
    redis_client.ping()
    logger.info(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}. Will use SQLite fallback.")
    redis_client = None


class RedisCache:
    """Обёртка над Redis с автоматическим fallback"""
    
    @staticmethod
    def is_available() -> bool:
        """Проверка доступности Redis"""
        if not redis_client:
            return False
        try:
            redis_client.ping()
            return True
        except:
            return False
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Получить значение из Redis"""
        if not redis_client:
            return None
        
        try:
            value = redis_client.get(key)
            if value:
                logger.debug(f"[REDIS] Cache HIT: {key}")
                return json.loads(value) if value else None
            logger.debug(f"[REDIS] Cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"[REDIS] Get error for {key}: {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = 1800) -> bool:
        """
        Сохранить значение в Redis
        ttl: время жизни в секундах (по умолчанию 30 минут)
        """
        if not redis_client:
            return False
        
        try:
            redis_client.setex(
                key, 
                ttl, 
                json.dumps(value, ensure_ascii=False)
            )
            logger.debug(f"[REDIS] Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Set error for {key}: {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """Удалить ключ из Redis (invalidation)"""
        if not redis_client:
            return False
        
        try:
            redis_client.delete(key)
            logger.debug(f"[REDIS] Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Delete error for {key}: {e}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """
        Удалить все ключи по паттерну
        Пример: delete_pattern("user:*") - удалит всех пользователей
        """
        if not redis_client:
            return 0
        
        try:
            keys = redis_client.keys(pattern)
            if keys:
                count = redis_client.delete(*keys)
                logger.info(f"[REDIS] Deleted {count} keys matching '{pattern}'")
                return count
            return 0
        except Exception as e:
            logger.warning(f"[REDIS] Delete pattern error for {pattern}: {e}")
            return 0
    
    @staticmethod
    def exists(key: str) -> bool:
        """Проверить существование ключа"""
        if not redis_client:
            return False
        
        try:
            return redis_client.exists(key) > 0
        except:
            return False
    
    @staticmethod
    def ttl(key: str) -> int:
        """Получить оставшееся время жизни ключа в секундах"""
        if not redis_client:
            return -1
        
        try:
            return redis_client.ttl(key)
        except:
            return -1
    
    @staticmethod
    def incr(key: str, amount: int = 1, ttl: int = None) -> Optional[int]:
        """
        Атомарно увеличить значение (для счётчиков)
        Если ttl указан - устанавливаем expire при создании
        """
        if not redis_client:
            return None
        
        try:
            value = redis_client.incrby(key, amount)
            if ttl and not redis_client.ttl(key) > 0:
                redis_client.expire(key, ttl)
            return value
        except Exception as e:
            logger.warning(f"[REDIS] Incr error for {key}: {e}")
            return None
    
    @staticmethod
    def decr(key: str, amount: int = 1) -> Optional[int]:
        """Атомарно уменьшить значение"""
        if not redis_client:
            return None
        
        try:
            return redis_client.decrby(key, amount)
        except Exception as e:
            logger.warning(f"[REDIS] Decr error for {key}: {e}")
            return None
    
    @staticmethod
    def get_info() -> dict:
        """Получить информацию о Redis (для мониторинга)"""
        if not redis_client:
            return {"status": "unavailable"}
        
        try:
            info = redis_client.info()
            return {
                "status": "connected",
                "memory_used": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands": info.get("total_commands_processed"),
                "keys": redis_client.dbsize()
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def hset(key: str, field: str, value: Any) -> bool:
        """Сохранить поле в хэше"""
        if not redis_client:
            return False
        
        try:
            redis_client.hset(key, field, json.dumps(value, ensure_ascii=False))
            # logger.debug(f"[REDIS] HSET: {key} -> {field}") # Too noisy
            return True
        except Exception as e:
            logger.warning(f"[REDIS] HSet error for {key}.{field}: {e}")
            return False

    @staticmethod
    def hget(key: str, field: str) -> Optional[Any]:
        """Получить поле из хэша"""
        if not redis_client:
            return None
        
        try:
            value = redis_client.hget(key, field)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"[REDIS] HGet error for {key}.{field}: {e}")
            return None

    @staticmethod
    def hvals(key: str) -> list:
        """Получить все значения из хэша"""
        if not redis_client:
            return []
        
        try:
            values = redis_client.hvals(key)
            return [json.loads(v) for v in values] if values else []
        except Exception as e:
            logger.warning(f"[REDIS] HVals error for {key}: {e}")
            return []

    @staticmethod
    def hdel(key: str, field: str) -> bool:
        """Удалить поле из хэша"""
        if not redis_client:
            return False
        
        try:
            redis_client.hdel(key, field)
            return True
        except Exception as e:
            logger.warning(f"[REDIS] HDel error for {key}.{field}: {e}")
            return False

    @staticmethod
    def hlen(key: str) -> int:
        """Количество полей в хэше"""
        if not redis_client:
            return 0
        
        try:
            return redis_client.hlen(key)
        except Exception as e:
            logger.warning(f"[REDIS] HLen error for {key}: {e}")
            return 0
    
    @staticmethod
    def expire(key: str, ttl: int) -> bool:
        """Установить TTL для ключа"""
        if not redis_client:
            return False
        try:
            redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Expire error for {key}: {e}")
            return False


# Экспортируем для удобства
cache = RedisCache()
