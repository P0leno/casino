"""
Модели для работы с Redis - обёртки над БД операциями
"""
import sqlite3
import json
from typing import Optional, List, Dict
from .redis_client import cache
from app.config import DB_PATH
import logging

logger = logging.getLogger(__name__)

# TTL константы (в секундах)
TTL_USER = 1800  # 30 минут
TTL_SHOP_GIFT = 3600  # 1 час
TTL_PROMO = 600  # 10 минут


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
            conn = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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
                conn2 = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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
            conn = sqlite3.connect(DB_PATH)
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


# Экспортируем для удобства
__all__ = ['RedisUser', 'RedisShopGift', 'RedisPromo', 'cache']
