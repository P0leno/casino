import asyncio
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN, LOG_BOT_TOKEN
from app.handlers import start, payments, admin

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(payments.router)

# Log bot для обработки callback в канале логов
if LOG_BOT_TOKEN:
    log_bot = Bot(token=LOG_BOT_TOKEN)
    log_dp = Dispatcher()
    log_dp.include_router(admin.router)
else:
    log_bot = None
    log_dp = None

async def start_bot():
    # Запускаем основного бота
    bot_task = asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем log bot если настроен
    if log_bot and log_dp:
        log_task = asyncio.create_task(log_dp.start_polling(log_bot))
        await asyncio.gather(bot_task, log_task)
    else:
        await bot_task

async def stop_bot():
    await bot.session.close()
    if log_bot:
        await log_bot.session.close()
