#!/usr/bin/env python3
"""
Скрипт для получения подарков из чата через Pyrogram
Запуск: python3 -m app.scripts.get_gifts
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from pyrogram import Client  # pyrofork устанавливается как pyrogram

# Загружаем переменные окружения
load_dotenv()

# Получаем данные из .env
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

async def main():
    # Создаем файл для записи результатов
    output_file = "gifts_output.txt"
    
    def log(message):
        """Печатает в консоль и записывает в файл"""
        print(message)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    
    # Очищаем файл перед началом
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("")
    
    log("🚀 Запуск скрипта получения подарков...")
    
    if not SESSION_STRING:
        log("❌ SESSION_STRING не найден в .env файле!")
        return
    
    if not API_ID or not API_HASH:
        log("❌ API_ID или API_HASH не найдены в .env файле!")
        return
    
    log(f"📝 API_ID: {API_ID}")
    log(f"📝 SESSION_STRING: {SESSION_STRING[:20]}...")
    
    # Создаем клиент из строки сессии
    app = Client(
        "gift_getter",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )
    
    try:
        log("\n🔄 Подключение к Telegram...")
        await app.start()
        
        # Получаем информацию о текущем пользователе
        me = await app.get_me()
        log(f"\n✅ Подключено как: {me.first_name} (@{me.username if me.username else 'no username'})")
        log(f"📱 User ID: {me.id}")
        
        # Получаем подарки через метод get_chat_gifts (async generator)
        log(f"\n🎁 Получение подарков через get_chat_gifts()...")
        log("📜 Итерация по результатам...\n")
        log("="*80)
        
        gifts_count = 0
        
        try:
            async for gift in app.get_chat_gifts(
                chat_id=me.id,
                exclude_unlimited=True,
                limit=100
            ):
                gifts_count += 1
                log(f"\n🎁 Подарок #{gifts_count}:")
                log(f"   Type: {type(gift)}")
                
                # Выводим все атрибуты
                if hasattr(gift, '__dict__'):
                    for key, value in gift.__dict__.items():
                        if not key.startswith('_'):
                            log(f"   {key}: {value}")
                else:
                    log(f"   Data: {gift}")
                
                log("-"*80)
            
            log(f"\n📊 Всего найдено подарков: {gifts_count}")
            
            if gifts_count == 0:
                log("\n⚠️  Подарков не найдено")
                log("💡 Возможно у аккаунта нет подарков или они все unlimited")
                
        except AttributeError as e:
            log(f"❌ Метод get_chat_gifts не найден: {e}")
            log("💡 Убедитесь что установлен pyrofork с поддержкой этого метода")
            
        except Exception as e:
            log(f"❌ Ошибка при получении подарков: {e}")
            log(f"   Тип ошибки: {type(e).__name__}")
            import traceback
            error_text = traceback.format_exc()
            log(error_text)
        
    except Exception as e:
        log(f"❌ Ошибка подключения: {e}")
        import traceback
        error_text = traceback.format_exc()
        log(error_text)
    
    finally:
        log("\n🔄 Отключение...")
        await app.stop()
        log("✅ Готово!")
        log(f"\n💾 Результаты сохранены в файл: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
