"""
Оптимизированное подключение к SQLite для высокой нагрузки
"""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "./users.db")

# Глобальные настройки для SQLite
SQLITE_TIMEOUT = 60  # 60 секунд ожидания при блокировке
SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WALИ  hn ",           # Write-Ahead Logging для параллельного доступа
    "PRAGMA synchronous=NORMAL",          # Баланс между скоростью и надёжностью
    "PRAGMA cache_size=-64000",           # 64MB кэш
    "PRAGMA temp_store=MEMORY",           # Временные таблицы в памяти
    "PRAGMA mmap_size=268435456",         # 256MB memory-mapped I/O
    "PRAGMA busy_timeout=60000",          # 60 секунд busy timeout
    "PRAGMA wal_autocheckpoint=1000",     # Checkpoint каждые 1000 страниц
]


def get_db_connection(timeout: int = SQLITE_TIMEOUT) -> sqlite3.Connection:
    """
    Получить оптимизированное соединение с БД
    
    Args:
        timeout: Время ожидания при блокировке (по умолчанию 60 сек)
    
    Returns:
        sqlite3.Connection с оптимальными настройками
    """
    conn = sqlite3.connect(DB_PATH, timeout=timeout, check_same_thread=False)
    
    # Применяем все PRAGMA настройки
    for pragma in SQLITE_PRAGMAS:
        try:
            conn.execute(pragma)
        except Exception as e:
            print(f"[DB] Warning: Failed to execute {pragma}: {e}")
    
    return conn


@contextmanager
def db_connection(timeout: int = SQLITE_TIMEOUT):
    """
    Context manager для автоматического закрытия соединения
    
    Usage:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
    """
    conn = get_db_connection(timeout)
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """
    Инициализация БД с оптимальными настройками.
    Вызывать один раз при старте приложения.
    """
    conn = get_db_connection()
    
    # Выполняем VACUUM для оптимизации (только при старте)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print("[DB] WAL checkpoint completed")
    except Exception as e:
        print(f"[DB] WAL checkpoint warning: {e}")
    
    conn.close()
    print("[DB] Database initialized with optimized settings")


# Инициализация при импорте модуля
_initialized = False

def ensure_initialized():
    global _initialized
    if not _initialized:
        init_database()
        _initialized = True
