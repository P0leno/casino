from app.utils.database import get_db_connection, DB_PATH
from datetime import datetime
from app.utils.database import get_db_connection, DB_PATH
import sqlite3

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            username TEXT,
            creation_date TEXT NOT NULL,
            is_banned INTEGER DEFAULT 0,
            last_spin_date TEXT,
            inventory TEXT DEFAULT '[]',
            balance INTEGER DEFAULT 0,
            bonus_balance INTEGER DEFAULT 0,
            last_spin_notification TEXT,
            ton_wallet_address TEXT,
            completed_tasks TEXT DEFAULT '[]'
        )
    """)
    
    # Автоматическая миграция: добавление last_spin_notification если его нет
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'last_spin_notification' not in columns:
            print("⚙️  Миграция: добавление поля last_spin_notification...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_spin_notification TEXT")
            conn.commit()
            print("✅ Миграция завершена: last_spin_notification добавлен")
        
        if 'ton_wallet_address' not in columns:
            print("⚙️  Миграция: добавление поля ton_wallet_address...")
            cursor.execute("ALTER TABLE users ADD COLUMN ton_wallet_address TEXT")
            conn.commit()
            print("✅ Миграция завершена: ton_wallet_address добавлен")
        
        if 'completed_tasks' not in columns:
            print("⚙️  Миграция: добавление поля completed_tasks...")
            cursor.execute("ALTER TABLE users ADD COLUMN completed_tasks TEXT DEFAULT '[]'")
            conn.commit()
            print("✅ Миграция завершена: completed_tasks добавлен")
        
        if 'username' not in columns:
            print("⚙️  Миграция: добавление поля username...")
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            conn.commit()
            print("✅ Миграция завершена: username добавлен")
        
        if 'user_id' not in columns:
            print("⚙️  Миграция: добавление поля user_id...")
            cursor.execute("ALTER TABLE users ADD COLUMN user_id INTEGER")
            conn.commit()
            print("✅ Миграция завершена: user_id добавлен")
        
        if 'activated_promocodes' not in columns:
            print("⚙️  Миграция: добавление поля activated_promocodes...")
            cursor.execute("ALTER TABLE users ADD COLUMN activated_promocodes TEXT DEFAULT '[]'")
            conn.commit()
            print("✅ Миграция завершена: activated_promocodes добавлен")
        
        if 'refbalance' not in columns:
            print("⚙️  Миграция: добавление поля refbalance...")
            cursor.execute("ALTER TABLE users ADD COLUMN refbalance INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Миграция завершена: refbalance добавлен")
        
        if 'avatar_url' not in columns:
            print("⚙️  Миграция: добавление поля avatar_url...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            conn.commit()
            print("✅ Миграция завершена: avatar_url добавлен")
        
        if 'support_banned' not in columns:
            print("⚙️  Миграция: добавление поля support_banned...")
            cursor.execute("ALTER TABLE users ADD COLUMN support_banned INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Миграция завершена: support_banned добавлен")
        
        if 'support_banned_until' not in columns:
            print("⚙️  Миграция: добавление поля support_banned_until...")
            cursor.execute("ALTER TABLE users ADD COLUMN support_banned_until TEXT")
            conn.commit()
            print("✅ Миграция завершена: support_banned_until добавлен")
        
        if 'ip_addresses' not in columns:
            print("⚙️  Миграция: добавление поля ip_addresses...")
            cursor.execute("ALTER TABLE users ADD COLUMN ip_addresses TEXT DEFAULT '[]'")
            conn.commit()
            print("✅ Миграция завершена: ip_addresses добавлен")
        
        if 'user_agents' not in columns:
            print("⚙️  Миграция: добавление поля user_agents...")
            cursor.execute("ALTER TABLE users ADD COLUMN user_agents TEXT DEFAULT '[]'")
            conn.commit()
            print("✅ Миграция завершена: user_agents добавлен")
        
        # Таблица для игнорируемых IP пар (антифрод)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS antifraud_ignored (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                user_ids TEXT NOT NULL,
                ignored_at TEXT NOT NULL
            )
        """)
        print("✅ Таблица antifraud_ignored создана/проверена")
        
        # Таблица для отправленных алертов (чтобы не спамить)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS antifraud_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        print("✅ Таблица antifraud_alerts создана/проверена")
        
    except Exception as e:
        print(f"⚠️  Ошибка миграции: {e}")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            mode TEXT DEFAULT 'free_spin',
            paw_min INTEGER DEFAULT 0,
            paw_max INTEGER DEFAULT 0,
            star_min INTEGER DEFAULT 1,
            star_max INTEGER DEFAULT 5,
            UNIQUE(gift_name, mode)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paid_spin_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            paw_min INTEGER DEFAULT 0,
            paw_max INTEGER DEFAULT 0,
            star_min INTEGER DEFAULT 1,
            star_max INTEGER DEFAULT 5
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL,
            gift_id TEXT
        )
    """)
    
    # Таблица настроек системы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Дефолтные настройки
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('stars_topup_enabled', 'true', 'Пополнение звездами')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('max_crash_multiplier', '10.0', 'Максимальный коэффициент краша')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('crash_always_profit', '0', 'Режим всегда в плюсе (0/1)')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('crash_max_debt', '300', 'Порог долга для агрессивного режима')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('crash_big_bet_threshold', '100', 'Порог большой ставки')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('crash_big_bet_lose_chance', '30', 'Шанс проигрыша на большой ставке (%)')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('admins', '[]', 'Список ID администраторов')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('ton_price_usd', '5.5', 'Цена TON в USD (CoinMarketCap)')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('shop_commission', '10', 'Наценка на подарки (%)')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('sell_commission', '10', 'Комиссия на продажу подарков (%)')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('custom_promo_refs_required', '10', 'Рефералов для именного промокода')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES ('maintenance_mode', '0', 'Режим технических работ (0/1)')")
    
    print("✅ Таблица settings создана/проверена")
    
    # Таблица моделей подарков (для синхронизации с Telegram Gift API)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_models (
            gift_name TEXT PRIMARY KEY,
            models TEXT NOT NULL,
            last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            folder_exists INTEGER DEFAULT 0
        )
    """)
    
    print("✅ Таблица gift_models создана/проверена")
    
    # Таблица для CryptoBot счетов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cryptobot_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            invoice_id INTEGER NOT NULL UNIQUE,
            amount_usdt REAL NOT NULL,
            amount_stars_expected INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            bot_invoice_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            confirmed_at TEXT,
            amount_stars_actual INTEGER,
            expires_at TEXT NOT NULL
        )
    """)
    
    print("✅ Таблица cryptobot_invoices создана/проверена")
    
    # УДАЛЯЕМ старую таблицу crash_settings (переносим в settings)
    try:
        cursor.execute("DROP TABLE IF EXISTS crash_settings")
        print("✅ Старая таблица crash_settings удалена (перенесено в settings)")
    except Exception as e:
        print(f"⚠️  Не удалось удалить crash_settings: {e}")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            type TEXT NOT NULL,
            award INTEGER NOT NULL,
            currency TEXT NOT NULL,
            custom_invite TEXT,
            execution_limit INTEGER,
            completions_count INTEGER DEFAULT 0
        )
    """)
    
    # Таблица промокодов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'ref',
            xp INTEGER NOT NULL DEFAULT 0,
            owner INTEGER NOT NULL,
            reward INTEGER NOT NULL DEFAULT 25,
            invited_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Таблица promocodes создана/проверена")
    
    # Таблица истории промокодов (активации и пополнения от рефералов)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            amount INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (promo_id) REFERENCES promocodes(id)
        )
    """)
    print("✅ Таблица promo_history создана/проверена")
    
    # Миграция: добавление invited_count если его нет
    try:
        cursor.execute("PRAGMA table_info(promocodes)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'invited_count' not in columns:
            print("⚙️  Миграция: добавление поля invited_count в promocodes...")
            cursor.execute("ALTER TABLE promocodes ADD COLUMN invited_count INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Миграция завершена: invited_count добавлен")
    except Exception as e:
        print(f"⚠️  Ошибка миграции promocodes: {e}")
    
    # Миграция: добавление поля custom_invite если его нет
    try:
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'custom_invite' not in columns:
            print("⚙️  Миграция: добавление поля custom_invite в tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN custom_invite TEXT")
            conn.commit()
            print("✅ Миграция завершена: custom_invite добавлен")
    except Exception as e:
        print(f"⚠️  Ошибка миграции tasks: {e}")
    
    # Миграция: добавление поля is_banned если его нет
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_banned' not in columns:
            print("⚙️  Миграция: добавление поля is_banned в users...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
            conn.commit()
            print("✅ Миграция завершена: is_banned добавлен")
    except Exception as e:
        print(f"⚠️  Ошибка миграции users: {e}")
    
    # Таблица диалогов поддержки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_dialogs (
            dialog_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            last_response_at TIMESTAMP,
            isPriority INTEGER DEFAULT 0
        )
    """)
    print("✅ Таблица support_dialogs создана/проверена")
    
    # Таблица сообщений диалогов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            sender_name TEXT,
            message_text TEXT,
            photo_path TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dialog_id) REFERENCES support_dialogs(dialog_id)
        )
    """)
    print("✅ Таблица dialog_messages создана/проверена")
    
    # Таблица сообщений поддержки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER NOT NULL,
            from_user INTEGER NOT NULL,
            message_text TEXT,
            photo_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dialog_id) REFERENCES support_dialogs(dialog_id)
        )
    """)
    print("✅ Таблица support_messages создана/проверена")
    
    # Таблица для подарков из магазина
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_id TEXT UNIQUE NOT NULL,
            slug TEXT DEFAULT NULL,
            title TEXT NOT NULL,
            model_name TEXT,
            model_path TEXT,
            symbol_name TEXT,
            backdrop_name TEXT,
            center_color TEXT,
            edge_color TEXT,
            pattern_color TEXT,
            text_color TEXT,
            available_amount INTEGER DEFAULT 0,
            total_amount INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0,
            ton_price REAL DEFAULT NULL,
            transfer_price INTEGER DEFAULT 25,
            rarity_model INTEGER DEFAULT NULL,
            rarity_symbol INTEGER DEFAULT NULL,
            rarity_backdrop INTEGER DEFAULT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            price_update TIMESTAMP DEFAULT NULL
        )
    """)
    print("✅ Таблица shop_gifts создана/проверена")
    
    # Миграция: добавление price_update если его нет
    try:
        cursor.execute("PRAGMA table_info(shop_gifts)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'price_update' not in columns:
            print("⚙️  Миграция: добавление поля price_update в shop_gifts...")
            cursor.execute("ALTER TABLE shop_gifts ADD COLUMN price_update TIMESTAMP DEFAULT NULL")
            conn.commit()
            print("✅ Миграция завершена: price_update добавлен")
        if 'ton_price' not in columns:
            print("⚙️  Миграция: добавление поля ton_price в shop_gifts...")
            cursor.execute("ALTER TABLE shop_gifts ADD COLUMN ton_price REAL DEFAULT NULL")
            conn.commit()
            print("✅ Миграция завершена: ton_price добавлен")
    except Exception as e:
        print(f"⚠️  Ошибка миграции shop_gifts: {e}")
    
    # Данные для бесплатного спина
    # star_min/star_max - только для 'star', paw_min/paw_max - только для 'paw'
    free_spin_gifts = [
        ('bear', 10.0, 1.0, 0, 0, 0, 0),
        ('cake', 10.0, 0.0, 0, 0, 0, 0),
        ('cup', 10.0, 0.0, 0, 0, 0, 0),
        ('diamond', 10.0, 0.0, 0, 0, 0, 0),
        ('flowers', 10.0, 0.0, 0, 0, 0, 0),
        ('gift', 10.0, 0.01, 0, 0, 0, 0),
        ('heart', 10.0, 1.0, 0, 0, 0, 0),
        ('ring', 10.0, 0.0, 0, 0, 0, 0),
        ('rocket', 10.0, 0.0, 0, 0, 0, 0),
        ('rose', 10.0, 0.0, 0, 0, 0, 0),
        ('bottle', 10.0, 0.0, 0, 0, 0, 0),
        ('paw', 10.0, 90.0, 1, 7, 0, 0),
        ('star', 10.0, 7.0, 0, 0, 1, 5)
    ]
    
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in free_spin_gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'free_spin', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
    
    # Данные для платного спина (бомж кейс) за 5 звезд
    # star_min/star_max - только для 'star', paw_min/paw_max - только для 'paw'
    bazmin_gifts = [
        ('bear', 10.0, 1.0, 0, 0, 0, 0),
        ('heart', 10.0, 1.0, 0, 0, 0, 0),
        ('rose', 10.0, 0.0, 0, 0, 0, 0),
        ('gift', 10.0, 0.01, 0, 0, 0, 0),
        ('star', 20.0, 98.0, 0, 0, 1, 4)  # Увеличили шанс star с 7.0 до 98.0 (забрали у paw)
    ]
    
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in bazmin_gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'bazmin', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
    
    # Данные для lapik спина (за 10 лапок)
    lapik_gifts = [
        ('bear', 10.0, 10.0, 0, 0, 0, 0),
        ('gift', 10.0, 10.0, 0, 0, 0, 0),
        ('heart', 10.0, 10.0, 0, 0, 0, 0),
        ('rose', 10.0, 10.0, 0, 0, 0, 0),
        ('star', 10.0, 10.0, 0, 0, 1, 4)
    ]
    
    for gift_name, visible, real, paw_min, paw_max, star_min, star_max in lapik_gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance, mode, paw_min, paw_max, star_min, star_max) VALUES (?, ?, ?, 'lapik', ?, ?, ?, ?)",
            (gift_name, visible, real, paw_min, paw_max, star_min, star_max)
        )
    
    prices = [
        ('bear', 15, '5170233102089322756'),
        ('cake', 50, '5170144170496491616'),
        ('cup', 100, '5168043875654172773'),
        ('diamond', 100, '5170521118301225164'),
        ('flowers', 50, '5170314324215857265'),
        ('gift', 25, '5170250947678437525'),
        ('heart', 15, '5170145012310081615'),
        ('ring', 100, '5170690322832818290'),
        ('rocket', 50, '5170564780938756245'),
        ('rose', 25, '5168103777563050263'),
        ('bottle', 0, '6028601630662853006')
    ]
    
    for gift_name, price, gift_id in prices:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_prices (gift_name, price, gift_id) VALUES (?, ?, ?)",
            (gift_name, price, gift_id)
        )
    
    conn.commit()
    conn.close()
