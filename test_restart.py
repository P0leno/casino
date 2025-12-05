#!/usr/bin/env python3
"""
Тестовый скрипт для проверки restart monitor
Отправляет команду "рестарт" в канал логов
"""
import asyncio
from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

LOG_BOT_TOKEN = os.getenv("LOG_BOT_TOKEN")
LOGS_ID = int(os.getenv("LOGS_ID", "0"))


async def test_restart():
    """Отправить команду рестарт в канал"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        print("❌ LOG_BOT_TOKEN or LOGS_ID не настроены в .env")
        return
    
    bot = Bot(token=LOG_BOT_TOKEN)
    
    try:
        # Отправляем команду
        await bot.send_message(
            chat_id=LOGS_ID,
            text="рестарт",
            parse_mode="HTML"
        )
        print("✅ Команда 'рестарт' отправлена в канал логов")
        print(f"   Канал: {LOGS_ID}")
        print("   Ожидайте сообщение о перезапуске...")
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    
    finally:
        await bot.session.close()


if __name__ == "__main__":
    print("🔄 Тест автоматического перезапуска")
    print("=" * 50)
    asyncio.run(test_restart())
