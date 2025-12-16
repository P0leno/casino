"""
Асинхронный пул соединений SQLite с aiosqlite

Решает проблему блокировок при высокой нагрузке:
- Connection pooling
- Автоматический retry при "database is locked"
- Единая точка входа для всех операций с БД
"""
import asyncio
import aiosqlite
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

# Настройки
DB_PATH = os.getenv("DB_PATH", "./users.db")
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
SQLITE_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_DELAY = 0.1  # секунды

# PRAGMA настройки для каждого соединения
SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA cache_size=-64000",
    "PRAGMA temp_store=MEMORY",
    "PRAGMA mmap_size=268435456",
    "PRAGMA busy_timeout=60000",
    "PRAGMA wal_autocheckpoint=1000",
]


class AsyncDBPool:
    """Асинхронный пул соединений SQLite"""
    
    def __init__(self, db_path: str = DB_PATH, pool_size: int = POOL_SIZE):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def init(self):
        """Инициализация пула соединений"""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info(f"[DB Pool] Initializing pool with {self.pool_size} connections...")
            
            for i in range(self.pool_size):
                conn = await self._create_connection()
                await self._pool.put(conn)
                logger.debug(f"[DB Pool] Created connection {i+1}/{self.pool_size}")
            
            self._initialized = True
            logger.info(f"[DB Pool] ✅ Pool initialized with {self.pool_size} connections")
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Создать новое соединение с оптимальными настройками"""
        conn = await aiosqlite.connect(
            self.db_path,
            timeout=SQLITE_TIMEOUT,
            isolation_level=None  # autocommit mode для WAL
        )
        
        # Применяем PRAGMA настройки
        for pragma in SQLITE_PRAGMAS:
            try:
                await conn.execute(pragma)
            except Exception as e:
                logger.warning(f"[DB Pool] Failed to execute {pragma}: {e}")
        
        # Row factory для dict-like доступа
        conn.row_factory = aiosqlite.Row
        
        return conn
    
    @asynccontextmanager
    async def connection(self):
        """
        Context manager для получения соединения из пула
        
        Usage:
            async with db_pool.connection() as conn:
                cursor = await conn.execute("SELECT * FROM users")
                rows = await cursor.fetchall()
        """
        if not self._initialized:
            await self.init()
        
        conn = await self._pool.get()
        try:
            yield conn
        finally:
            # Возвращаем соединение в пул
            try:
                await self._pool.put(conn)
            except asyncio.QueueFull:
                # Пул переполнен - закрываем лишнее соединение
                await conn.close()
    
    async def execute(
        self, 
        query: str, 
        params: Tuple = (), 
        retries: int = MAX_RETRIES
    ) -> aiosqlite.Cursor:
        """
        Выполнить запрос с автоматическим retry при блокировке
        
        Returns:
            aiosqlite.Cursor
        """
        last_error = None
        
        for attempt in range(retries):
            try:
                async with self.connection() as conn:
                    cursor = await conn.execute(query, params)
                    return cursor
            except Exception as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg or "busy" in error_msg:
                    last_error = e
                    delay = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"[DB Pool] Database locked, retry {attempt+1}/{retries} in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_error or Exception("Failed to execute query after retries")
    
    async def execute_with_commit(
        self,
        query: str,
        params: Tuple = (),
        retries: int = MAX_RETRIES
    ) -> int:
        """
        Выполнить запрос с commit и retry
        
        Returns:
            Количество затронутых строк
        """
        last_error = None
        
        for attempt in range(retries):
            try:
                async with self.connection() as conn:
                    cursor = await conn.execute(query, params)
                    await conn.commit()
                    return cursor.rowcount
            except Exception as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg or "busy" in error_msg:
                    last_error = e
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"[DB Pool] Database locked on commit, retry {attempt+1}/{retries}")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_error or Exception("Failed to execute query with commit after retries")
    
    async def fetchone(
        self,
        query: str,
        params: Tuple = ()
    ) -> Optional[aiosqlite.Row]:
        """Выполнить запрос и вернуть одну строку"""
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            return await cursor.fetchone()
    
    async def fetchall(
        self,
        query: str,
        params: Tuple = ()
    ) -> List[aiosqlite.Row]:
        """Выполнить запрос и вернуть все строки"""
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            return await cursor.fetchall()
    
    async def close(self):
        """Закрыть все соединения в пуле"""
        logger.info("[DB Pool] Closing all connections...")
        
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
        
        self._initialized = False
        logger.info("[DB Pool] ✅ All connections closed")


# Глобальный экземпляр пула
db_pool = AsyncDBPool()


def retry_on_locked(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """
    Декоратор для автоматического retry при блокировке БД
    
    Usage:
        @retry_on_locked(max_retries=3)
        async def my_db_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "database is locked" in error_msg or "busy" in error_msg:
                        last_error = e
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"[DB Retry] {func.__name__} locked, "
                            f"attempt {attempt+1}/{max_retries}, "
                            f"waiting {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            
            raise last_error or Exception(f"{func.__name__} failed after {max_retries} retries")
        
        return wrapper
    return decorator


# Хелперы для частых операций
async def get_user(user_id: int) -> Optional[dict]:
    """Получить пользователя по ID"""
    row = await db_pool.fetchone(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )
    return dict(row) if row else None


async def update_user(user_id: int, **fields) -> bool:
    """Обновить поля пользователя"""
    if not fields:
        return False
    
    import json
    
    set_parts = []
    values = []
    
    for key, value in fields.items():
        set_parts.append(f"{key} = ?")
        if key in ['inventory', 'activated_promocodes', 'completed_tasks']:
            values.append(json.dumps(value) if isinstance(value, (list, dict)) else value)
        else:
            values.append(value)
    
    values.append(user_id)
    
    query = f"UPDATE users SET {', '.join(set_parts)} WHERE id = ?"
    rows_affected = await db_pool.execute_with_commit(query, tuple(values))
    
    return rows_affected > 0


# Экспорт
__all__ = [
    'db_pool',
    'AsyncDBPool', 
    'retry_on_locked',
    'get_user',
    'update_user',
]
