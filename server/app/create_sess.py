#!/usr/bin/env python3
"""
Скрипт для создания Pyrogram session string
Запустите: python3 app/create_sess.py
"""
import asyncio
from pyrogram import Client

async def main():
    print("=" * 50)
    print("🔐 Создание Pyrogram Session String")
    print("=" * 50)
    print()
    
    # Запрашиваем данные
    api_id = input("Введите API_ID (с https://my.telegram.org): ").strip()
    api_hash = input("Введите API_HASH: ").strip()
    
    if not api_id or not api_hash:
        print("❌ API_ID и API_HASH обязательны!")
        return
    
    print()
    print("📱 Сейчас вам придет код в Telegram...")
    print()
    
    # Создаем временный клиент
    async with Client(
        name="temp_session",
        api_id=int(api_id),
        api_hash=api_hash,
        in_memory=True
    ) as app:
        # Экспортируем session string
        session_string = await app.export_session_string()
        
        print()
        print("=" * 50)
        print("✅ Session string успешно создан!")
        print("=" * 50)
        print()
        print("Скопируйте эту строку в .env файл:")
        print()
        print(f"SESSION_STRING={session_string}")
        print()
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
