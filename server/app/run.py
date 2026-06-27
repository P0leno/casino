import asyncio
import uvicorn
import signal
import sys
import logging

# Ensure logs are flushed immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from contextlib import asynccontextmanager
from fastapi import FastAPI

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app.run")
logger.info("=== RUN.PY LOADED === VERSION: 2024-12-24-v2 ===")

# Apply Runtime Patches
from app.utils.library_patch import apply_pyrogram_patches
apply_pyrogram_patches()


from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, admin, payments, crash, tasks, shop, inventory, promocode, ban, cryptobot_payments, spins, nft
from app.routers.spins import legacy_router
from app.bot import start_bot, stop_bot
from app.log_bot import start_log_bot, stop_log_bot
from app.pyrogram_client import start_pyrogram, stop_pyrogram
from app.tasks.spin_notifications import spin_notification_loop
from app.tasks.ton_transaction_checker import ton_transaction_loop
from app.tasks.gift_parser import gift_parser_loop
from app.tasks.ton_price_updater import ton_price_loop
from app.tasks.gift_models_checker import gift_models_checker_loop
from app.tasks.antifraud import antifraud_task
from app.crash_game import start_crash_game_loop, crash_game
from app.support_bot import start_support_bot
from app.tasks.redis_sync import start_redis_sync, stop_redis_sync
from app.utils.redis_client import cache, redis_client
from app.restart_monitor import start_restart_monitor, stop_restart_monitor, get_restart_message_id, clear_restart_message_id, send_status_to_channel
from app.utils.aiosqlite_pool import db_pool
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.limiter import limiter

# Инициализация лимитера (перенесена в app.utils.limiter)

bot_task = None
log_bot_task = None
pyrogram_task = None
notification_task = None
crash_task = None
ton_checker_task = None
gift_parser_task = None
ton_price_task = None
gift_models_task = None
support_bot_task = None
cryptobot_checker_task = None
redis_sync_task = None
restart_monitor_task = None
gift_ingestion_task = None
backup_task = None

app = FastAPI(title="Shelloch API", docs_url=None, redoc_url=None)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting error handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router)
app.include_router(spins.router) # Replaces game
app.include_router(legacy_router)  # Backward-compat: /api/spin, /api/check-spin-available
app.include_router(nft.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(crash.router)
app.include_router(tasks.router)
app.include_router(shop.router)
app.include_router(inventory.router)
app.include_router(promocode.router)
app.include_router(ban.router)
app.include_router(cryptobot_payments.router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, log_bot_task, pyrogram_task, notification_task, crash_task, ton_checker_task, gift_parser_task, ton_price_task, gift_models_task, support_bot_task, cryptobot_checker_task, redis_sync_task, restart_monitor_task, gift_ingestion_task, backup_task
    
    # Инициализация БД
    init_db()
    
    # Инициализация асинхронного пула соединений
    await db_pool.init()
    print("✅ Async DB pool initialized")
    
    # Загрузка админов из ENV в Redis
    from app.utils.redis_models import RedisSettings
    RedisSettings.load_admins_from_env()
    
    # Запуск Telegram бота
    bot_task = asyncio.create_task(start_bot())
    
    # Запуск бота логов (для callback в канале)
    log_bot_task = asyncio.create_task(start_log_bot())
    print("✅ Запущен бот логов для обработки callback")
    
    # Запуск Pyrogram клиента и регистрация хендлеров
    try:
        from app.pyrogram_client import start_pyrogram, get_pyrogram
        started = await start_pyrogram()
        
        if started:
            # Регистрируем хендлеры авто-инджеста
            from app.utils.gift_ingestion import register_gift_handlers
            app_client = get_pyrogram()
            if app_client:
                register_gift_handlers(app_client)
                print("✅ Хендлеры Gift Ingestion зарегистрированы")
                
                # Запускаем Keep-Alive loop
                from app.pyrogram_client import keep_alive_loop
                # Используем глобальную переменную для таска (добавим если нет, но лучше в lifespan scope)
                asyncio.create_task(keep_alive_loop())
                print("✅ Pyrogram Keep-Alive loop запущен")
            else:
                print("⚠️  Pyrogram клиент не получен после старта")
        else:
            print("⚠️  Pyrogram не запущен")
            
    except Exception as e:
        print(f"⚠️  Ошибка инициализации Pyrogram: {e}")
        import traceback
        traceback.print_exc()
    
    # Запуск фоновой задачи уведомлений о спинах
    notification_task = asyncio.create_task(spin_notification_loop())
    print("✅ Запущена фоновая задача уведомлений о фри спинах")
    
    # Запуск краш-игры
    crash_task = asyncio.create_task(start_crash_game_loop())
    print("✅ Запущена краш-игра")
    
    # Запуск проверки TON транзакций
    ton_checker_task = asyncio.create_task(ton_transaction_loop())
    print("✅ Запущен мониторинг TON транзакций")
    
    # ========================================
    # ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ДАННЫХ (при старте)
    # ========================================
    
    from app.tasks.gift_parser import full_sync_with_prices
    from app.tasks.ton_price_updater import update_ton_price, recalculate_gift_prices
    
    print("=" * 80)
    print("🚀 ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ДАННЫХ")
    print("=" * 80)
    print()
    
    # 1. Обновляем курс TON сначала
    print("1️⃣  Обновление цены TON с CoinMarketCap...")
    await update_ton_price()
    
    # 2. Синхронизируем количество подарков в магазине (восстанавливаем консистентность)
    from app.utils.shop_sync import sync_shop_amounts
    print("2️⃣  Синхронизация количества подарков (Shop Consistency Check)...")
    await asyncio.to_thread(sync_shop_amounts)
    
    print()
    print("2️⃣  Полная синхронизация подарков (Telegram + Tonnel + пересчет цен)...")
    print("   ⏭️  Пропущено - будет выполнено в фоновом режиме через минуту")
    
    # 3. Синхронизируем состояние краш игры и базы банвордов
    # Это выполняется внутри start_crash_game_loop
    
    # НЕ запускаем синхронизацию при старте - слишком долго (20 минут)
    # Будет выполнена автоматически фоновой задачей
    
    # Первичный бекап БД при старте
    from app.utils.db_backup import backup_db as run_initial_backup
    run_initial_backup()
    print("✅ Первичный бекап БД создан")

    print()
    print("=" * 80)
    print("✅ ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ЗАВЕРШЕНА")
    print("=" * 80)
    print()
    
    # ========================================
    # ЗАПУСК ЦИКЛИЧЕСКИХ ЗАДАЧ
    # ========================================
    
    # Запуск проверки полученных подарков (gift parser)
    gift_parser_task = asyncio.create_task(gift_parser_loop())
    print("✅ Запущен парсер подарков")
    
    # Запуск обновления цены TON
    ton_price_task = asyncio.create_task(ton_price_loop())
    print("✅ Запущен авто-апдейтер цены TON")
    
    # Запуск проверки моделей подарков (Lottie)
    gift_models_task = asyncio.create_task(gift_models_checker_loop())
    print("✅ Запущен чекер моделей подарков (Lottie)")
    
    # Бот поддержки (polling mode)
    support_bot_task = asyncio.create_task(start_support_bot())
    print("✅ Запущен бот поддержки (polling mode)")
    
    # CryptoBot checker (каждые 30 секунд)
    from app.tasks.cryptobot_invoice_checker import cryptobot_checker_loop
    cryptobot_checker_task = asyncio.create_task(cryptobot_checker_loop())
    print("✅ Запущен CryptoBot Invoice Checker (каждые 30 секунд)")
    
    # Антифрод система (каждые 5 минут)
    antifraud_check_task = asyncio.create_task(antifraud_task())
    print("✅ Запущена антифрод система (каждые 5 минут)")
    
    # Запуск авто-бекапа БД (каждые 6 часов)
    from app.utils.db_backup import backup_loop as start_backup_loop
    backup_task = asyncio.create_task(start_backup_loop())
    print("✅ Запущен авто-бекап БД (каждые 6 часов)")

    # Запуск Redis синхронизации
    if cache.is_available():
        # Загружаем settings в Redis при старте
        from app.utils.redis_models import RedisSettings
        print("📥 Загрузка настроек в Redis...")
        RedisSettings.load_all_to_redis()
        
        await start_redis_sync()
        print("✅ Redis синхронизация запущена (каждые 5 минут)")
        redis_info = cache.get_info()
        print(f"   📊 Redis: {redis_info.get('keys', 0)} keys, {redis_info.get('memory_used', 'N/A')}")
    else:
        print("⚠️  Redis недоступен, работаем только с SQLite")
    
    # Запуск монитора перезапуска
    await start_restart_monitor()
    
    # Проверяем, был ли это рестарт
    restart_msg_id = await get_restart_message_id()
    logger.info(f"DEBUG: Startup check - Restart Msg ID from DB: {restart_msg_id}")
    
    if restart_msg_id:
        logger.info(f"🔄 Обнаружен рестарт (msg_id={restart_msg_id}). Обновляем статус...")
        try:
            # Небольшая задержка чтобы бот успел подключиться
            await asyncio.sleep(2.0)
            
            # Мы используем log_bot который уже запущен в start_log_bot
            # Но нам нужен объект бота. Импортируем его
            from app.log_bot import log_bot
            
            logger.info(f"DEBUG: Calling send_status_to_channel for msg {restart_msg_id}")
            await send_status_to_channel(
                log_bot,
                "✅ <b>Сервер успешно перезапущен!</b>\n\n"
                "🚀 Все системы работают в штатном режиме.\n"
                "🎲 Краш-игра готова к приему ставок.",
                restart_msg_id
            )
            logger.info("DEBUG: send_status_to_channel finished")
            await clear_restart_message_id()
            logger.info("DEBUG: clear_restart_message_id finished")
        except Exception as e:
            logger.error(f"⚠️ Ошибка обновления статуса рестарта: {e}")
            import traceback
            # Log traceback to logger instead of stdout if possible, or just use logger.exception
            logger.error("Traceback:", exc_info=True)
    else:
        logger.info("DEBUG: No restart message ID found. Normal startup or ID lost.")
        # Обычный запуск (не рестарт) — отправляем сообщение в логи
        try:
            from app.log_bot import send_message_to_logs
            import os
            LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
            if LOG_CHANNEL_ID:
                await send_message_to_logs(
                    "✅ <b>Скрипт запущен!</b>\n\n"
                    "🚀 Все системы инициализированы\n"
                    "🤖 Боты подключены\n"
                    "💎 Синхронизация активна"
                )
                print("✅ Отправлено сообщение о запуске в логи")
        except Exception as e:
            print(f"⚠️ Ошибка отправки сообщения о запуске: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        yield
    except asyncio.CancelledError:
        print("🛑 Lifespan cancelled (shutting down)...")
    
    # Graceful shutdown logic defined purely
    async def shutdown_cleanup():
        logger.info("🛑 SHUTDOWN_CLEANUP: Начинается остановка сервисов...")
        
        # 1. Останавливаем мониторинг (быстро)
        logger.info("🛑 SHUTDOWN_CLEANUP: Step 1 - Stopping restart_monitor...")
        if restart_monitor_task:
            await stop_restart_monitor()
        logger.info("🛑 SHUTDOWN_CLEANUP: Step 1 - DONE")
        
        # 2. Crash Game Graceful Shutdown (ДОЛГО - до 30с)
        logger.info("🛑 SHUTDOWN_CLEANUP: Step 2 - Stopping crash game (waiting for round end)...")
        try:
            await asyncio.wait_for(crash_game.shutdown_gracefully(), timeout=30.0)
            logger.info("🛑 SHUTDOWN_CLEANUP: Step 2 - Crash game stopped SUCCESSFULLY")
        except asyncio.TimeoutError:
            logger.error("⚠️ SHUTDOWN_CLEANUP: Crash game shutdown TIMEOUT (30s)")
        except Exception as e:
            logger.error(f"⚠️ SHUTDOWN_CLEANUP: Crash game error: {e}")
            
        if crash_task:
            logger.info("🛑 SHUTDOWN_CLEANUP: Cancelling crash_task...")
            crash_task.cancel()

        # 3. Redis Sync (сохранение данных)
        logger.info("🛑 SHUTDOWN_CLEANUP: Step 3 - Stopping Redis sync...")
        if redis_sync_task:
            try:
                await stop_redis_sync()
            except Exception as e:
                logger.error(f"⚠️ Redis sync stop error: {e}")
        logger.info("🛑 SHUTDOWN_CLEANUP: Step 3 - DONE")

        # 4. Закрываем DB pool (в самом конце)
        logger.info("� SHUTDOWN_CLEANUP: Step 4 - Closing DB pool...")
        try:
            await db_pool.close()
            logger.info("✅ SHUTDOWN_CLEANUP: DB pool closed")
        except Exception as e:
            logger.error(f"⚠️ DB pool close error: {e}")
        
        logger.info("🛑 SHUTDOWN_CLEANUP: ALL STEPS COMPLETE")

    try:
        logger.info("🛑 LIFESPAN SHUTDOWN: Starting cleanup with asyncio.shield...")
        # Запускаем cleanup в защищенном режиме, чтобы CancelledError основного таска не прервал его
        # В Python 3.12 asyncio.shield работает надежно
        await asyncio.shield(shutdown_cleanup())
        logger.info("🛑 LIFESPAN SHUTDOWN: Cleanup finished successfully")
    except asyncio.CancelledError:
        # Если shield не помог (иногда бывает), мы все равно ждем завершения
        # Но shield должен работать.
        logger.warning("⚠️ Lifespan cancelled, but cleanup should have finished via shield.")
        pass
    except Exception as e:
        logger.error(f"⚠️ Ошибка при shutdown cleanup: {e}")

    # После этого продолжаем закрывать остальные некритичные таски
    
    # Закрываем Redis connection pool
    if redis_client:
        try:
            redis_client.close()
            print("✅ Redis connections closed")
        except Exception as e:
            print(f"⚠️  Redis close error: {e}")
    
    # Останавливаем CryptoBot checker
    if cryptobot_checker_task:
        cryptobot_checker_task.cancel()
        try:
            await asyncio.wait_for(cryptobot_checker_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  CryptoBot checker не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем фоновую задачу уведомлений
    if notification_task:
        notification_task.cancel()
        try:
            await asyncio.wait_for(notification_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Notification task не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем TON checker
    if ton_checker_task:
        ton_checker_task.cancel()
        try:
            await asyncio.wait_for(ton_checker_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  TON checker task не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем gift parser
    if gift_parser_task:
        gift_parser_task.cancel()
        try:
            await asyncio.wait_for(gift_parser_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Gift parser task не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем TON price updater
    if ton_price_task:
        ton_price_task.cancel()
        try:
            await asyncio.wait_for(ton_price_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  TON price task не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем gift models checker
    if gift_models_task:
        gift_models_task.cancel()
        try:
            await asyncio.wait_for(gift_models_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Gift models task не завершился")
        except asyncio.CancelledError:
            pass
    
    # Останавливаем Pyrogram с таймаутом
    try:
        await asyncio.wait_for(stop_pyrogram(), timeout=3.0)
    except asyncio.TimeoutError:
        print("⚠️  Pyrogram не остановился за 3 секунды")
    except Exception as e:
        print(f"⚠️  Ошибка остановки Pyrogram: {e}")
    
    # Останавливаем основного бота с таймаутом
    if bot_task:
        bot_task.cancel()
        try:
            await asyncio.wait_for(bot_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Bot task не завершился")
        except asyncio.CancelledError:
            pass
    
    try:
        await asyncio.wait_for(stop_bot(), timeout=3.0)
    except asyncio.TimeoutError:
        print("⚠️  Bot не остановился за 3 секунды")
    except Exception as e:
        print(f"⚠️  Ошибка остановки бота: {e}")
    
    # Останавливаем бота логов
    if log_bot_task:
        log_bot_task.cancel()
        try:
            await asyncio.wait_for(log_bot_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Log bot task не завершился")
        except asyncio.CancelledError:
            pass
    
    try:
        await asyncio.wait_for(stop_log_bot(), timeout=3.0)
    except asyncio.TimeoutError:
        print("⚠️  Log bot не остановился за 3 секунды")
    except Exception as e:
        print(f"⚠️  Ошибка остановки log bot: {e}")
    
    # Останавливаем бота поддержки
    if support_bot_task:
        support_bot_task.cancel()
        try:
            await asyncio.wait_for(support_bot_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Support bot task не завершился")
        except asyncio.CancelledError:
            pass
    
    print("✅ Все сервисы остановлены")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Shell Api",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,  # Отключаем /openapi.json
        lifespan=lifespan  # ВАЖНО: подключаем lifespan для graceful shutdown
    )

    # Подключаем Limiter к приложению
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware для проверки бана
    from app.middlewares.ban_check import ban_check_middleware
    
    # Middleware проверки бана
    app.middleware("http")(ban_check_middleware)
    
    # Middleware для технических работ
    from app.middlewares.maintenance import maintenance_middleware
    app.middleware("http")(maintenance_middleware)

    app.include_router(auth.router)
    app.include_router(spins.router)
    app.include_router(admin.router)
    app.include_router(payments.router)
    app.include_router(crash.router)
    app.include_router(tasks.router)
    app.include_router(shop.router)
    app.include_router(inventory.router)
    app.include_router(promocode.router)
    app.include_router(ban.router)
    app.include_router(cryptobot_payments.router)
    
    return app

def run_server():
    app = create_app()
    
    # Uvicorn сам обрабатывает SIGTERM/SIGINT корректно
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=3779,
        loop="asyncio",
        log_level="info",
        timeout_graceful_shutdown=10  # Даем 10 секунд на graceful shutdown
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"Server stopped with error: {e}")
    finally:
        # Принудительно завершаем процесс, чтобы systemd мог его перезапустить
        print("🛑 Uvicorn stopped, forcing exit...")
        import os
        os._exit(0)
