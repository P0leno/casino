import asyncio
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers import start, payments

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(payments.router)

async def start_bot():
    await dp.start_polling(bot)

async def stop_bot():
    await bot.session.close()
