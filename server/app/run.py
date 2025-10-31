import asyncio
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, game, admin, payments, crash
from app.bot import start_bot, stop_bot
from app.pyrogram_client import start_pyrogram, stop_pyrogram
from app.tasks.spin_notifications import spin_notification_loop
from app.crash_game import start_crash_game_loop

bot_task = None
pyrogram_task = None
notification_task = None
crash_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, pyrogram_task, notification_task, crash_task
    
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
    
    yield
    
    # Graceful shutdown
    print("🛑 Начинается остановка сервисов...")
    
    # Останавливаем фоновую задачу уведомлений
    if notification_task:
        notification_task.cancel()
        try:
            await asyncio.wait_for(notification_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("⚠️  Notification task не завершился")
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
    
    print("✅ Все сервисы остановлены")

def create_app():
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(game.router)
    app.include_router(admin.router)
    app.include_router(payments.router)
    app.include_router(crash.router)

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
