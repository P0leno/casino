import asyncio
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database.db import init_db
from app.routers import auth, game, admin, payments
from app.bot import start_bot, stop_bot

bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    init_db()
    bot_task = asyncio.create_task(start_bot())
    yield
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    await stop_bot()

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

@app.get("/")
async def root():
    return {"message": "Welcome to Shell Api"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

def signal_handler(signum, frame):
    print(f"\nПолучен сигнал {signum}, завершаем работу...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=3779,
        loop="asyncio",
        log_level="info"
    )
    server = uvicorn.Server(config)
    server.run()
