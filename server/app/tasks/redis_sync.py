"""
Фоновая синхронизация данных между Redis и SQLite
Запускается как background task
"""
import asyncio
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
import json
import logging
from datetime import datetime
from app.config import DB_PATH
from app.utils.redis_models import RedisUser, RedisShopGift, RedisPromo, cache
from app.utils.error_logger import send_error_log

logger = logging.getLogger(__name__)

# Интервал синхронизации (секунды)
SYNC_INTERVAL = 300  # 5 минут


class RedisSync:
    """Синхронизация данных между Redis и SQLite"""
    
    def __init__(self):
        self.is_running = False
        self.last_sync = None
        self.stats = {
            "users_synced": 0,
            "gifts_synced": 0,
            "promos_synced": 0,
            "errors": 0
        }
    
    async def start(self):
        """Запуск фоновой синхронизации"""
        if self.is_running:
            logger.warning("[SYNC] Already running")
            return
        
        self.is_running = True
        logger.info("[SYNC] Background sync started")
        
        while self.is_running:
            try:
                await self.sync_all()
                self.last_sync = datetime.now()
                
                # Логируем статистику
                logger.info(
                    f"[SYNC] Completed: users={self.stats['users_synced']}, "
                    f"gifts={self.stats['gifts_synced']}, "
                    f"promos={self.stats['promos_synced']}, "
                    f"errors={self.stats['errors']}"
                )
                
            except Exception as e:
                logger.error(f"[SYNC] Error: {e}")
                await send_error_log(e, "redis_sync.py: RedisSync loop")
                self.stats['errors'] += 1
            
            # Ждём следующей синхронизации
            await asyncio.sleep(SYNC_INTERVAL)
    
    async def sync_all(self):
        """Синхронизировать все данные"""
        if not cache.is_available():
            logger.warning("[SYNC] Redis unavailable, skipping sync")
            return
        
        # Синхронизируем по очереди
        await self.sync_hot_users()
        await self.sync_shop_gifts()
        await self.sync_hot_promos()
    
    async def sync_hot_users(self, limit: int = 1000):
        """
        Синхронизировать "горячих" пользователей
        Загружаем пользователей с активностью за последние 24 часа
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Получаем активных пользователей (пример - можно добавить last_activity)
            # Пока просто берём всех, кто не забанен
            cursor.execute("""
                SELECT id FROM users 
                WHERE is_banned = 0
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            count = 0
            for row in rows:
                user_id = row[0]
                # Если пользователь уже в Redis - обновляем
                if cache.exists(f"user:{user_id}"):
                    RedisUser.invalidate(user_id)  # Сбросим кэш
                    RedisUser.get(user_id)  # Перезагрузим свежие данные
                    count += 1
            
            self.stats['users_synced'] = count
            logger.debug(f"[SYNC] {count} users synced")
            
        except Exception as e:
            logger.error(f"[SYNC] Error syncing users: {e}")
            self.stats['errors'] += 1
    
    async def sync_shop_gifts(self):
        """Синхронизировать все подарки магазина"""
        try:
            # Invalidate старый кэш
            RedisShopGift.invalidate_all()
            
            # Загружаем свежие данные
            gifts = RedisShopGift.get_all()
            
            self.stats['gifts_synced'] = len(gifts)
            logger.debug(f"[SYNC] {len(gifts)} gifts synced")
            
        except Exception as e:
            logger.error(f"[SYNC] Error syncing gifts: {e}")
            self.stats['errors'] += 1
    
    async def sync_hot_promos(self, limit: int = 100):
        """Синхронизировать активные промокоды"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Получаем все промокоды (они не очень большие)
            cursor.execute("SELECT promo FROM promocodes LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            
            count = 0
            for row in rows:
                promo_code = row[0]
                # Если промокод в Redis - обновляем
                if cache.exists(f"promo:{promo_code}"):
                    cache.delete(f"promo:{promo_code}")
                    RedisPromo.get(promo_code)
                    count += 1
            
            self.stats['promos_synced'] = count
            logger.debug(f"[SYNC] {count} promos synced")
            
        except Exception as e:
            logger.error(f"[SYNC] Error syncing promos: {e}")
            self.stats['errors'] += 1
    
    async def stop(self):
        """Остановить синхронизацию"""
        logger.info("[SYNC] Stopping background sync...")
        self.is_running = False
    
    def get_stats(self) -> dict:
        """Получить статистику синхронизации"""
        return {
            "is_running": self.is_running,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "stats": self.stats,
            "redis_info": cache.get_info()
        }


# Singleton instance
sync_manager = RedisSync()


async def start_redis_sync():
    """Запустить фоновую синхронизацию (вызывать при старте приложения)"""
    asyncio.create_task(sync_manager.start())
    logger.info("[SYNC] Redis sync task created")


async def stop_redis_sync():
    """Остановить синхронизацию (вызывать при shutdown)"""
    await sync_manager.stop()
    logger.info("[SYNC] Redis sync stopped")
