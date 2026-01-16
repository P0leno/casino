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
    "PRAGMA journal_mode=WAL",           # Write-Ahead Logging для параллельного доступа
    "PRAGMA synchronous=NORMAL",          # Баланс между скоростью и надёжностью
    "PRAGMA cache_size=-64000",           # 64MB кэш
    "PRAGMA temp_store=MEMORY",           # Временные таблицы в памяти
    "PRAGMA mmap_size=268435456",         # 256MB memory-mapped I/O
    "PRAGMA busy_timeout=60000",          # 60 секунд busy timeout
    "PRAGMA wal_autocheckpoint=1000",     # Checkpoint каждые 1000 страниц
]


def init_sold_gifts_table(conn):
    """Создает таблицу sold_gifts если она не существует"""
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sold_gifts (
            slug TEXT PRIMARY KEY,
            user_id INTEGER,
            purchased_at TEXT
        )
        """)
    except Exception as e:
        print(f"[DB] Error creating sold_gifts table: {e}")

def init_payments_table(conn):
    """Создает таблицу payments для истории операций"""
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            method TEXT,
            is_promo INTEGER DEFAULT 0,
            type TEXT, -- 'income' or 'expense'
            date TEXT
        )
        """)
        # Index on user_id for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")
    except Exception as e:
        print(f"[DB] Error creating payments table: {e}")


def init_cases_table(conn):
    """Создает таблицу cases и заполняет дефолтными данными. Автомиграция."""
    try:
        # 1. Создаем таблицу если нет
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            slug TEXT PRIMARY KEY,
            title TEXT,
            price INTEGER,
            currency TEXT, -- 'star' or 'paw'
            is_active BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            spin_limit INTEGER DEFAULT -1 -- -1 means unlimited
        )
        """)
        
        # 2. Проверяем и добавляем колонки если таблица старая
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'is_default' not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN is_default BOOLEAN DEFAULT 0")
            print("[DB] Added column is_default to cases")
            

        if 'spin_limit' not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN spin_limit INTEGER DEFAULT -1")
            print("[DB] Added column spin_limit to cases")
            
        if 'spins_count' not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN spins_count INTEGER DEFAULT 0")
            print("[DB] Added column spins_count to cases")
            
        conn.commit()
        
        # 3. Сидинг дефолтных
        cursor.execute("SELECT count(*) FROM cases")
        if cursor.fetchone()[0] == 0:
            default_cases = [
                ('free_spin', 'Free Spin', 0, 'star', 1, 1, -1, 0),
                ('bazmin', 'Бомж Кейс', 10, 'star', 1, 1, -1, 0),
                ('lapik', 'Кейс Лапика', 50, 'star', 1, 1, -1, 0),
                ('nistart', 'Нистарт', 10, 'star', 1, 1, -1, 0),
                ('promik', 'Промо Кейс', 0, 'star', 1, 1, -1, 0)
            ]
            cursor.executemany(
                "INSERT INTO cases (slug, title, price, currency, is_active, is_default, spin_limit, spins_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                default_cases
            )
            conn.commit()
            print("[DB] Seeded default cases")
            
        # 4. Проверяем и исправляем настройки Lapik кейса (Force Fix)
        # Пользователь сообщает о проблеме с ценой/валютой
        try:
            conn.execute("UPDATE cases SET price = 10, currency = 'paw' WHERE slug = 'lapik'")
            conn.commit()
            # print("[DB] Enforced Lapik case settings") # Optional log
        except Exception as e:
            print(f"[DB] Error enforcing Lapik settings: {e}")

    except Exception as e:
        print(f"[DB] Error creating/migrating cases table: {e}")


def init_case_spins_table(conn):
    """Создает таблицу для трекинга прокрутов лимитированных кейсов"""
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_case_spins (
            user_id INTEGER,
            case_slug TEXT,
            count INTEGER DEFAULT 0,
            updated_at TEXT,
            PRIMARY KEY (user_id, case_slug)
        )
        """)
    except Exception as e:
        print(f"[DB] Error creating user_case_spins table: {e}")

def init_nft_cache_table(conn):
    """Создает таблицу для кэширования NFT подарков пользователя (TTL 1 час)"""
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_nft_cache (
            user_id INTEGER PRIMARY KEY,
            gifts_data TEXT,
            updated_at TEXT
        )
        """)
    except Exception as e:
        print(f"[DB] Error creating user_nft_cache table: {e}")

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
            
    # HACK: Проверяем наличие таблиц (быстрый фикс для удаленных серверов)
    init_sold_gifts_table(conn)
    init_payments_table(conn)
    init_cases_table(conn) # Auto-migrate cases
    init_case_spins_table(conn)
    init_nft_cache_table(conn)
    
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
