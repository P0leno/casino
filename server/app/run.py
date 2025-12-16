import asyncio
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, game, admin, payments, crash, ton_payments, tasks, shop, inventory, promocode, ban, maintenance, cryptobot_payments, maintenance_check
from app.bot import start_bot, stop_bot
from app.log_bot import start_log_bot, stop_log_bot
from app.pyrogram_client import start_pyrogram, stop_pyrogram
from app.tasks.spin_notifications import spin_notification_loop
from app.tasks.ton_transaction_checker import ton_transaction_loop
from app.tasks.gift_parser import gift_parser_loop
from app.tasks.ton_price_updater import ton_price_loop
from app.tasks.gift_models_checker import gift_models_checker_loop
from app.tasks.antifraud import antifraud_task
from app.crash_game import start_crash_game_loop
from app.support_bot import start_support_bot
from app.tasks.redis_sync import start_redis_sync, stop_redis_sync
from app.utils.redis_client import cache, redis_client
from app.restart_monitor import start_restart_monitor, stop_restart_monitor, get_restart_message_id, clear_restart_message_id, send_status_to_channel
from app.utils.aiosqlite_pool import db_pool

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, log_bot_task, pyrogram_task, notification_task, crash_task, ton_checker_task, gift_parser_task, ton_price_task, gift_models_task, support_bot_task, cryptobot_checker_task, redis_sync_task, restart_monitor_task
    
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
    
    # Запуск Pyrogram клиента
    try:
        await start_pyrogram()
    except Exception as e:
        print(f"⚠️  Pyrogram не запущен: {e}")
    
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
    
    print()
    print("2️⃣  Полная синхронизация подарков (Telegram + Tonnel + пересчет цен)...")
    print("   ⏭️  Пропущено - будет выполнено в фоновом режиме через минуту")
    
    # НЕ запускаем синхронизацию при старте - слишком долго (20 минут)
    # Будет выполнена автоматически фоновой задачей
    
    print()
    print("=" * 80)
    print("✅ ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ЗАВЕРШЕНА")
    print("=" * 80)
    print()
    
    # ========================================
    # ЗАПУСК ЦИКЛИЧЕСКИХ ЗАДАЧ
    # ========================================
    
    # Полная синхронизация подарков (каждый час): parse_gifts + Tonnel + новые/удаленные
    gift_parser_task = asyncio.create_task(gift_parser_loop())
    print("✅ Запущена полная синхронизация подарков (каждый час)")
    
    # Обновление цены TON + пересчет (каждые 5 минут)
    ton_price_task = asyncio.create_task(ton_price_loop())
    print("✅ Запущено обновление цены TON + пересчет (каждые 5 минут)")
    
    # Мониторинг моделей подарков (каждый час)
    gift_models_task = asyncio.create_task(gift_models_checker_loop())
    print("✅ Запущен мониторинг моделей подарков (каждый час)")
    
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
    
    # Запуск мониторинга перезапуска через канал логов
    await start_restart_monitor()
    print("✅ Мониторинг перезапуска запущен (команда: 'рестарт' в канале логов)")
    
    # Проверяем, был ли рестарт - обновляем сообщение в канале
    restart_message_id = get_restart_message_id()
    if restart_message_id:
        print(f"🔄 Обнаружен рестарт, обновляю сообщение {restart_message_id}...")
        try:
            from app.log_bot import log_bot
            
            # Отправляем финальное сообщение об успешном старте
            await send_status_to_channel(
                log_bot,
                "✅ <b>Сервер успешно запущен!</b>\n\n"
                "🚀 Все системы работают\n"
                "🎲 Краш-игра запущена\n"
                "🤖 Боты подключены\n"
                "💎 Синхронизация активна",
                restart_message_id
            )
            
            # Очищаем message_id из БД
            clear_restart_message_id()
            print("✅ Сообщение о рестарте обновлено")
        except Exception as e:
            print(f"⚠️ Ошибка обновления сообщения о рестарте: {e}")
    else:
        # Обычный запуск (не рестарт) — отправляем сообщение в логи
        try:
            from app.log_bot import log_bot, send_message_to_logs
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
    
    yield
    
    # Graceful shutdown
    print("🛑 Начинается остановка сервисов...")
    
    # Останавливаем restart monitor
    if restart_monitor_task:
        print("🛑 Останавливаем мониторинг перезапуска...")
        await stop_restart_monitor()
        print("✅ Мониторинг перезапуска остановлен")
    
    # КРИТИЧНО: Закрываем async DB pool
    print("💾 Closing async DB pool...")
    await db_pool.close()
    print("✅ Async DB pool closed")
    
    # КРИТИЧНО: Останавливаем Redis sync ПЕРВЫМ (сохраняем данные)
    if redis_sync_task:
        print("💾 Сохранение данных из Redis...")
        await stop_redis_sync()
        print("✅ Redis синхронизация остановлена")
    
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

def create_app():
    app = FastAPI(
        lifespan=lifespan,
        docs_url=None,  # Отключаем /docs
        redoc_url=None,  # Отключаем /redoc
        openapi_url=None  # Отключаем /openapi.json
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware для проверки бана
    from app.middlewares.ban_check import ban_check_middleware
    from app.middlewares.maintenance import maintenance_middleware
    
    # Middleware проверки бана
    app.middleware("http")(ban_check_middleware)
    
    # Middleware для проверки технических работ
    app.middleware("http")(maintenance_middleware)

    app.include_router(auth.router)
    app.include_router(game.router)
    app.include_router(admin.router)
    app.include_router(payments.router)
    app.include_router(crash.router)
    app.include_router(ton_payments.router)
    app.include_router(tasks.router)
    app.include_router(shop.router)
    app.include_router(inventory.router)
    app.include_router(promocode.router)
    app.include_router(ban.router)
    app.include_router(maintenance.router)
    app.include_router(cryptobot_payments.router)
    app.include_router(maintenance_check.router)

    @app.get("/")
    async def root():
        return {"message": "Welcome to Shell Api"}

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}
    
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
    server.run()
