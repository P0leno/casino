"""
Модели для работы с Redis - обёртки над БД операциями
"""
import sqlite3
import json
import os
from typing import Optional, List, Dict
from .redis_client import cache
import logging

logger = logging.getLogger(__name__)

# Database settings
DB_PATH = os.getenv("DB_PATH", "./users.db")
SQLITE_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_DELAY = 0.5

def _get_conn():
    """Получить оптимизированное соединение с retry логикой при блокировках"""
    import time
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT, check_same_thread=False, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")      # 64MB кэш
            conn.execute("PRAGMA temp_store=MEMORY")       # Временные таблицы в памяти
            conn.execute("PRAGMA mmap_size=268435456")     # 256MB memory-mapped I/O
            conn.execute("PRAGMA busy_timeout=120000")     # 120 секунд busy timeout
            conn.execute("PRAGMA wal_autocheckpoint=1000") # Checkpoint каждые 1000 страниц
            conn.execute("PRAGMA read_uncommitted=1")      # Грязное чтение для ускорения
            return conn
        except sqlite3.OperationalError as e:
            last_error = e
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[DB] Database locked, retry {attempt + 1}/{MAX_RETRIES} after {delay}s")
                time.sleep(delay)
            else:
                raise
    
    raise last_error

# TTL константы (в секундах)
TTL_USER = 1800  # 30 минут
TTL_SHOP_GIFT = 3600  # 1 час
TTL_PROMO = 600  # 10 минут
TTL_SETTINGS = 3600  # 1 час для настроек


class RedisUser:
    """Работа с пользователями через Redis + SQLite"""
    
    @staticmethod
    def get(user_id: int) -> Optional[Dict]:
        """
        Получить пользователя (сначала Redis, потом SQLite)
        Возвращает: {id, balance, bonus_balance, inventory, activated_promocodes, ...}
        """
        key = f"user:{user_id}"
        
        # Пытаемся Redis
        user = cache.get(key)
        if user:
            return user
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, username, balance, bonus_balance, 
                       inventory, activated_promocodes, is_banned, completed_tasks
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            user = {
                "id": row[0],
                "user_id": row[1],
                "username": row[2] or "",
                "balance": row[3] or 0,
                "bonus_balance": row[4] or 0,
                "inventory": json.loads(row[5] or "[]"),
                "activated_promocodes": json.loads(row[6] or "[]"),
                "is_banned": bool(row[7]),
                "completed_tasks": json.loads(row[8] or "[]")
            }
            
            # Сохраняем в Redis для следующих запросов
            cache.set(key, user, TTL_USER)
            logger.info(f"[CACHE] User {user_id} loaded from DB → Redis")
            
            return user
            
        except Exception as e:
            logger.error(f"[DB] Error loading user {user_id}: {e}")
            return None
    
    @staticmethod
    def update(user_id: int, **fields) -> bool:
        """
        Обновить пользователя (СНАЧАЛА SQLite, потом Redis)
        Пример: update(123, balance=1000, inventory=['gift1'])
        """
        if not fields:
            return False
        
        try:
            # 1. Обновляем SQLite (источник истины!)
            conn = _get_conn()
            cursor = conn.cursor()
            
            # Формируем SQL
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = []
            
            for k, v in fields.items():
                if k in ['inventory', 'activated_promocodes', 'completed_tasks']:
                    values.append(json.dumps(v))
                else:
                    values.append(v)
            
            values.append(user_id)
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"[DB] User {user_id} updated: {list(fields.keys())}, rows_affected: {rows_affected}")
            
            if rows_affected == 0:
                logger.warning(f"[DB] ⚠️ User {user_id} not found in DB, update had no effect!")
                return False
            
            # 2. КРИТИЧНО: Сначала инвалидируем Redis, потом СРАЗУ загружаем свежие данные
            key = f"user:{user_id}"
            deleted = cache.delete(key)
            logger.info(f"[CACHE] Step 1: Invalidated {key}, deleted: {deleted}")
            
            # Загружаем свежие данные НАПРЯМУЮ из БД и сохраняем в Redis
            try:
                conn2 = _get_conn()
                cursor2 = conn2.cursor()
                cursor2.execute("""
                    SELECT id, user_id, username, balance, bonus_balance, 
                           inventory, activated_promocodes, is_banned, completed_tasks
                    FROM users WHERE id = ?
                """, (user_id,))
                
                row = cursor2.fetchone()
                conn2.close()
                
                if row:
                    fresh_user = {
                        "id": row[0],
                        "user_id": row[1],
                        "username": row[2] or "",
                        "balance": row[3] or 0,
                        "bonus_balance": row[4] or 0,
                        "inventory": json.loads(row[5] or "[]"),
                        "activated_promocodes": json.loads(row[6] or "[]"),
                        "is_banned": bool(row[7]),
                        "completed_tasks": json.loads(row[8] or "[]")
                    }
                    
                    # СРАЗУ сохраняем в Redis
                    cache.set(key, fresh_user, TTL_USER)
                    logger.info(f"[CACHE] Step 2: Fresh data saved to Redis for user:{user_id}, completed_tasks: {fresh_user.get('completed_tasks', [])}")
                else:
                    logger.warning(f"[CACHE] ⚠️ User {user_id} not found in DB after update")
            except Exception as cache_error:
                logger.error(f"[CACHE] Error reloading user {user_id}: {cache_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"[DB] Error updating user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def update_balance(user_id: int, balance: int = None, bonus_balance: int = None) -> bool:
        """Быстрое обновление только баланса"""
        fields = {}
        if balance is not None:
            fields['balance'] = balance
        if bonus_balance is not None:
            fields['bonus_balance'] = bonus_balance
        
        return RedisUser.update(user_id, **fields)
    
    @staticmethod
    def invalidate(user_id: int):
        """Принудительно удалить пользователя из кэша"""
        cache.delete(f"user:{user_id}")


class RedisShopGift:
    """Работа с подарками магазина через Redis + SQLite"""
    
    @staticmethod
    def get(slug: str) -> Optional[Dict]:
        """
        Получить подарок по slug
        Возвращает: {slug, title, price, available_amount, ...}
        """
        key = f"shop:gift:{slug}"
        
        # Пытаемся Redis
        gift = cache.get(key)
        if gift:
            return gift
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gift_id, title, price, available_amount, slug, updated_at
                FROM shop_gifts WHERE slug = ?
            """, (slug,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            gift = {
                "gift_id": row[0],
                "title": row[1],
                "price": row[2] or 0,
                "available_amount": row[3] or 0,
                "slug": row[4],
                "updated_at": row[5]
            }
            
            # Кэшируем
            cache.set(key, gift, TTL_SHOP_GIFT)
            logger.info(f"[CACHE] Gift {slug} loaded from DB → Redis")
            
            return gift
            
        except Exception as e:
            logger.error(f"[DB] Error loading gift {slug}: {e}")
            return None
    
    @staticmethod
    def get_all() -> List[Dict]:
        """Получить все подарки"""
        key = "shop:gifts:all"
        
        # Пытаемся Redis
        slugs = cache.get(key)
        if slugs:
            # Получаем все подарки из Redis
            gifts = []
            for slug in slugs:
                gift = RedisShopGift.get(slug)
                if gift:
                    gifts.append(gift)
            return gifts
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gift_id, title, price, available_amount, slug, updated_at
                FROM shop_gifts
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            gifts = []
            slugs = []
            
            for row in rows:
                gift = {
                    "gift_id": row[0],
                    "title": row[1],
                    "price": row[2] or 0,
                    "available_amount": row[3] or 0,
                    "slug": row[4],
                    "updated_at": row[5]
                }
                gifts.append(gift)
                slugs.append(row[4])
                
                # Кэшируем каждый подарок
                cache.set(f"shop:gift:{row[4]}", gift, TTL_SHOP_GIFT)
            
            # Кэшируем список slug'ов
            cache.set(key, slugs, TTL_SHOP_GIFT)
            logger.info(f"[CACHE] {len(gifts)} gifts loaded from DB → Redis")
            
            return gifts
            
        except Exception as e:
            logger.error(f"[DB] Error loading all gifts: {e}")
            return []
    
    @staticmethod
    def update_amount(slug: str, new_amount: int) -> bool:
        """Обновить доступное количество (атомарно)"""
        try:
            # 1. Обновляем SQLite
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE shop_gifts 
                SET available_amount = ?
                WHERE slug = ?
            """, (new_amount, slug))
            conn.commit()
            conn.close()
            
            # 2. Invalidate Redis
            cache.delete(f"shop:gift:{slug}")
            cache.delete("shop:gifts:all")
            
            logger.info(f"[DB] Gift {slug} amount updated: {new_amount}")
            return True
            
        except Exception as e:
            logger.error(f"[DB] Error updating gift {slug}: {e}")
            return False
    
    @staticmethod
    def invalidate_all():
        """Удалить все подарки из кэша"""
        cache.delete_pattern("shop:gift:*")
        cache.delete("shop:gifts:all")


class RedisPromo:
    """Работа с промокодами через Redis + SQLite"""
    
    @staticmethod
    def get(promo_code: str) -> Optional[Dict]:
        """Получить промокод"""
        key = f"promo:{promo_code.upper()}"
        
        # Пытаемся Redis
        promo = cache.get(key)
        if promo:
            return promo
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, owner, promo, reward, type, invited_count
                FROM promocodes WHERE promo = ?
            """, (promo_code.upper(),))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            promo = {
                "id": row[0],
                "owner": row[1],
                "promo": row[2],
                "reward": row[3],
                "type": row[4],
                "invited_count": row[5] or 0
            }
            
            # Кэшируем
            cache.set(key, promo, TTL_PROMO)
            logger.info(f"[CACHE] Promo {promo_code} loaded from DB → Redis")
            
            return promo
            
        except Exception as e:
            logger.error(f"[DB] Error loading promo {promo_code}: {e}")
            return None
    
    @staticmethod
    def increment_invited(promo_code: str) -> bool:
        """Увеличить счётчик приглашённых"""
        try:
            # 1. Обновляем SQLite
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE promocodes 
                SET invited_count = invited_count + 1
                WHERE promo = ?
            """, (promo_code.upper(),))
            conn.commit()
            conn.close()
            
            # 2. Invalidate Redis
            cache.delete(f"promo:{promo_code.upper()}")
            
            logger.info(f"[DB] Promo {promo_code} invited_count incremented")
            return True
            
        except Exception as e:
            logger.error(f"[DB] Error incrementing promo {promo_code}: {e}")
            return False


class RedisSettings:
    """Работа с настройками через Redis + SQLite"""
    
    @staticmethod
    def get(key: str) -> Optional[Dict]:
        """
        Получить одну настройку по ключу
        Возвращает: {value, description, updated_at}
        """
        redis_key = f"setting:{key}"
        
        # Пытаемся Redis
        setting = cache.get(redis_key)
        if setting:
            return setting
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value, description, updated_at
                FROM settings WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            setting = {
                "value": row[0],
                "description": row[1] or "",
                "updated_at": row[2]
            }
            
            # Кэшируем
            cache.set(redis_key, setting, TTL_SETTINGS)
            logger.info(f"[CACHE] Setting {key} loaded from DB → Redis")
            
            return setting
            
        except Exception as e:
            logger.error(f"[DB] Error loading setting {key}: {e}")
            return None
    
    @staticmethod
    def get_value(key: str, default=None):
        """
        Быстрое получение значения настройки
        Возвращает только value или default
        """
        setting = RedisSettings.get(key)
        if setting:
            return setting.get('value', default)
        return default
    
    @staticmethod
    def get_float(key: str, default: float = 0.0) -> float:
        """Получить настройку как float"""
        value = RedisSettings.get_value(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """Получить настройку как int"""
        value = RedisSettings.get_value(key, default)
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """Получить настройку как bool (1/0 или true/false)"""
        value = RedisSettings.get_value(key, str(default))
        return value in ('1', 'true', 'True', True)
    
    @staticmethod
    def get_admins() -> list:
        """Получить список ID админов из Redis"""
        value = RedisSettings.get_value('admins', '[]')
        try:
            import json
            return json.loads(value) if value else []
        except:
            return []
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверить является ли пользователь админом"""
        admins = RedisSettings.get_admins()
        return user_id in admins
    
    @staticmethod
    def load_admins_from_env():
        """Загрузить админов из ENV в Redis"""
        import os
        import json
        
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        if not admin_ids_str:
            logger.warning("ADMIN_IDS not found in ENV")
            return []
        
        try:
            # Парсим из строки "123,456,789" или "[123,456,789]"
            admin_ids_str = admin_ids_str.strip()
            if admin_ids_str.startswith('['):
                admin_ids = json.loads(admin_ids_str)
            else:
                admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
            
            admin_ids_json = json.dumps(admin_ids)
            
            # Сохраняем в SQLite (создаем если нет)
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, description, updated_at)
                VALUES ('admins', ?, 'Список ID администраторов', CURRENT_TIMESTAMP)
            """, (admin_ids_json,))
            conn.commit()
            conn.close()
            
            # Сохраняем в Redis
            cache.set("setting:admins", {"value": admin_ids_json, "description": "Список ID администраторов"}, TTL_SETTINGS)
            
            logger.info(f"✅ Loaded {len(admin_ids)} admins to Redis: {admin_ids}")
            return admin_ids
        except Exception as e:
            logger.error(f"❌ Error loading admins from ENV: {e}")
            return []
    
    @staticmethod
    def get_all() -> Dict[str, Dict]:
        """
        Получить все настройки
        Возвращает: {key1: {value, description}, key2: {...}, ...}
        """
        redis_key = "settings:all"
        
        # Пытаемся Redis
        settings = cache.get(redis_key)
        if settings:
            logger.debug(f"[CACHE] Settings loaded from Redis, count: {len(settings)}")
            return settings
        
        # Fallback на SQLite
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value, description, updated_at
                FROM settings
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            settings = {}
            for row in rows:
                key = row[0]
                settings[key] = {
                    "value": row[1],
                    "description": row[2] or "",
                    "updated_at": row[3]
                }
                
                # Кэшируем каждую настройку отдельно
                cache.set(f"setting:{key}", settings[key], TTL_SETTINGS)
            
            # Кэшируем весь словарь настроек
            cache.set(redis_key, settings, TTL_SETTINGS)
            logger.info(f"[CACHE] {len(settings)} settings loaded from DB → Redis")
            
            return settings
            
        except Exception as e:
            logger.error(f"[DB] Error loading all settings: {e}")
            return {}
    
    @staticmethod
    def set(key: str, value: str) -> bool:
        """
        Обновить настройку (СНАЧАЛА SQLite, потом Redis)
        """
        try:
            # 1. Обновляем SQLite (источник истины!)
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE settings 
                SET value = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE key = ?
            """, (value, key))
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_affected == 0:
                logger.warning(f"[DB] ⚠️ Setting {key} not found in DB, update had no effect!")
                return False
            
            logger.info(f"[DB] Setting {key} updated to: {value}")
            
            # 2. Invalidate Redis кэш
            cache.delete(f"setting:{key}")
            cache.delete("settings:all")
            
            # 3. СРАЗУ загружаем свежие данные в Redis
            fresh_setting = RedisSettings.get(key)
            if fresh_setting:
                logger.info(f"[CACHE] Setting {key} reloaded: {fresh_setting['value']}")
            
            # 4. Перезагружаем весь словарь настроек
            all_settings = RedisSettings.get_all()
            logger.info(f"[CACHE] All settings reloaded, count: {len(all_settings)}")
            
            return True
            
        except Exception as e:
            logger.error(f"[DB] Error updating setting {key}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def invalidate(key: str = None):
        """
        Принудительно удалить настройку(и) из кэша
        Если key=None, удаляет все настройки
        """
        if key:
            cache.delete(f"setting:{key}")
        else:
            cache.delete_pattern("setting:*")
        
        cache.delete("settings:all")
        logger.info(f"[CACHE] Settings invalidated: {key or 'ALL'}")
    
    @staticmethod
    def load_all_to_redis():
        """
        Принудительная загрузка всех настроек в Redis при старте
        """
        try:
            # Сначала очищаем старый кэш
            RedisSettings.invalidate()
            
            # Загружаем все настройки
            settings = RedisSettings.get_all()
            
            logger.info(f"✅ Settings loaded to Redis: {len(settings)} keys")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading settings to Redis: {e}")
            return False


# Экспортируем для удобства
__all__ = ['RedisUser', 'RedisShopGift', 'RedisPromo', 'RedisSettings', 'cache']
