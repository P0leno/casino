import asyncio
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers import start, payments
from app.utils.error_logger import send_error_log

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(payments.router)

# Подключаем админ-обработчики (для кнопок в логах)
from app.handlers import admin as admin_handlers
from app.handlers import gift_callbacks
dp.include_router(admin_handlers.router)
dp.include_router(gift_callbacks.router)

async def start_bot():
    try:
        print("[MAIN_BOT] Запуск основного бота...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[MAIN_BOT] Ошибка: {e}")
        await send_error_log(e, "bot.py: start_bot")
        raise

async def stop_bot():
    try:
        print("[MAIN_BOT] Остановка основного бота...")
        await bot.session.close()
    except Exception as e:
        print(f"[MAIN_BOT] Ошибка остановки: {e}")
        await send_error_log(e, "bot.py: stop_bot")
