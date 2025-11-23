import asyncio
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, game, admin, payments, crash, ton_payments, tasks, shop, inventory, promocode, ban, maintenance, cryptobot_payments
from app.bot import start_bot, stop_bot
from app.pyrogram_client import start_pyrogram, stop_pyrogram
from app.tasks.spin_notifications import spin_notification_loop
from app.tasks.ton_transaction_checker import ton_transaction_loop
from app.tasks.gift_parser import gift_parser_loop
from app.tasks.price_updater import price_update_loop
from app.tasks.ton_price_updater import ton_price_loop
from app.crash_game import start_crash_game_loop
from app.support_bot import start_support_bot

bot_task = None
pyrogram_task = None
notification_task = None
crash_task = None
ton_checker_task = None
gift_parser_task = None
price_updater_task = None
ton_price_task = None
support_bot_task = None
cryptobot_checker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, pyrogram_task, notification_task, crash_task, ton_checker_task, gift_parser_task, price_updater_task, ton_price_task, support_bot_task, cryptobot_checker_task
    
    # Инициализация БД
    init_db()
    
    # Запуск Telegram бота
    bot_task = asyncio.create_task(start_bot())
    
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
    
    # 1. Парсинг подарков через Pyrogram (получаем LIMITED NFT)
    from app.tasks.gift_parser import parse_gifts
    from app.tasks.ton_price_updater import update_ton_price, recalculate_gift_prices
    from app.tasks.price_updater import update_all_prices
    
    print("=" * 80)
    print("🚀 ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ДАННЫХ")
    print("=" * 80)
    print()
    
    print("1️⃣  Парсинг подарков через Pyrogram...")
    try:
        await parse_gifts()
    except Exception as e:
        print(f"⚠️  Ошибка парсинга подарков: {e}")
    
    print()
    print("2️⃣  Обновление цены TON с CoinMarketCap...")
    await update_ton_price()
    
    print()
    print("3️⃣  Обновление цен LIMITED NFT с Tonnel...")
    await update_all_prices()
    
    print()
    print("4️⃣  Пересчет цен подарков в звезды...")
    await recalculate_gift_prices()
    
    print()
    print("=" * 80)
    print("✅ ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ЗАВЕРШЕНА")
    print("=" * 80)
    print()
    
    # ========================================
    # ЗАПУСК ЦИКЛИЧЕСКИХ ЗАДАЧ
    # ========================================
    
    # Парсер подарков (каждые 5 минут)
    gift_parser_task = asyncio.create_task(gift_parser_loop())
    print("✅ Запущен парсер подарков (каждые 5 минут)")
    
    # Обновление цены TON + пересчет (каждые 5 минут)
    ton_price_task = asyncio.create_task(ton_price_loop())
    print("✅ Запущено обновление цены TON + пересчет (каждые 5 минут)")
    
    # Обновление цен с Tonnel (каждый час)
    price_updater_task = asyncio.create_task(price_update_loop())
    print("✅ Запущено обновление цен с Tonnel (каждый час)")
    
    # Бот поддержки (polling mode)
    support_bot_task = asyncio.create_task(start_support_bot())
    print("✅ Запущен бот поддержки (polling mode)")
    
    # CryptoBot checker (каждые 30 секунд)
    from app.tasks.cryptobot_invoice_checker import cryptobot_checker_loop
    cryptobot_checker_task = asyncio.create_task(cryptobot_checker_loop())
    print("✅ Запущен CryptoBot Invoice Checker (каждые 30 секунд)")
    
    yield
    
    # Graceful shutdown
    print("🛑 Начинается остановка сервисов...")
    
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
    
    # Останавливаем price updater
    if price_updater_task:
        price_updater_task.cancel()
        try:
            await asyncio.wait_for(price_updater_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Price updater task не завершился")
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
    
    # Останавливаем Pyrogram с таймаутом
    try:
        await asyncio.wait_for(stop_pyrogram(), timeout=3.0)
    except asyncio.TimeoutError:
        print("⚠️  Pyrogram не остановился за 3 секунды")
    except Exception as e:
        print(f"⚠️  Ошибка остановки Pyrogram: {e}")
    
    # Останавливаем бота с таймаутом
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
    
    # Middleware проверки бана
    app.middleware("http")(ban_check_middleware)
    
    # Maintenance проверяется в эндпоинте /api/validate, не в middleware

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
