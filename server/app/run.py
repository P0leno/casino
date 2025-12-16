import asyncio
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, game, admin, payments, crash, tasks, shop, inventory, promocode, ban, cryptobot_payments
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
    
    # 3. Синхронизируем состояние краш игры и базы банвордов
    # Это выполняется внутри start_crash_game_loop
    
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
        print("🛑 Начинается остановка сервисов (cleanup)...")
        
        # 1. Останавливаем мониторинг (быстро)
        if restart_monitor_task:
            await stop_restart_monitor()
        
        # 2. Crash Game Graceful Shutdown (ДОЛГО - до 30с)
        print("🛑 Останавливаем краш-игру (ждем конца раунда)...")
        try:
             # Shielding не нужен здесь, так как мы уже внутри shielded shutdown_cleanup
            await asyncio.wait_for(crash_game.shutdown_gracefully(), timeout=30.0)
        except Exception as e:
            print(f"⚠️ Ошибка shutdown краш-игры: {e}")
            
        if crash_task:
            crash_task.cancel()

        # 3. Redis Sync (сохранение данных)
        if redis_sync_task:
            print("💾 Сохранение данных из Redis...")
            try:
                await stop_redis_sync()
            except Exception as e:
                 print(f"⚠️ Redis sync stop error: {e}")

        # 4. Закрываем DB pool (в самом конце)
        print("💾 Closing async DB pool...")
        try:
            await db_pool.close()
            print("✅ Async DB pool closed")
        except Exception as e:
            print(f"⚠️ DB pool close error: {e}")

    try:
        # Запускаем cleanup в защищенном режиме, чтобы CancelledError основного таска не прервал его
        # В Python 3.12 asyncio.shield работает надежно
        await asyncio.shield(shutdown_cleanup())
    except asyncio.CancelledError:
        # Если shield не помог (иногда бывает), мы все равно ждем завершения
        # Но shield должен работать.
        print("⚠️ Lifespan cancelled, but cleanup should have finished via shield.")
        pass
    except Exception as e:
        print(f"⚠️ Ошибка при shutdown cleanup: {e}")

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
        docs_url="/docs",
        redoc_url=None,
        openapi_url=None  # Отключаем /openapi.json
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
    app.include_router(game.router)
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
