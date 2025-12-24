"""
Инициализация Pyrogram клиента для отправки подарков
"""
import os

# Глобальный клиент
pyrogram_app = None
Client = None

def init_pyrogram():
    """Инициализирует Pyrogram клиент"""
    global pyrogram_app, Client
    
    # Ленивый импорт - только когда нужно
    try:
        from pyrogram import Client as PyrogramClient
        Client = PyrogramClient
    except ImportError:
        print("⚠️  Pyrogram не установлен - отправка подарков недоступна")
        return None
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING', None)
    
    if not api_id or not api_hash:
        print("⚠️  API_ID или API_HASH не установлены - Pyrogram не инициализирован")
        return None
    
    pyrogram_app = Client(
        name="gift_sender",
        api_id=int(api_id),
        api_hash=api_hash,
        session_string=session_string,
        workdir="./sessions"
    )
    
    print("✅ Pyrogram клиент инициализирован")
    return pyrogram_app


async def start_pyrogram():
    """Запускает Pyrogram клиент"""
    global pyrogram_app
    
    if pyrogram_app is None:
        init_pyrogram()
    
    if pyrogram_app:
        try:
            await pyrogram_app.start()
            print("✅ Pyrogram клиент запущен")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска Pyrogram: {e}")
            return False
    return False


async def stop_pyrogram():
    """Корректно останавливает Pyrogram клиент"""
    global pyrogram_app
    
    if pyrogram_app:
        try:
            await pyrogram_app.stop()
            print("✅ Pyrogram клиент остановлен")
        except Exception as e:
            print(f"⚠️  Ошибка остановки Pyrogram: {e}")


async def reconnect_pyrogram():
    """
    Переподключает Pyrogram клиент при потере соединения.
    Используется при ошибках TCPTransport closed.
    """
    global pyrogram_app
    
    print("🔄 Переподключение Pyrogram...")
    
    # Сначала пробуем остановить текущий клиент
    if pyrogram_app:
        try:
            if pyrogram_app.is_connected:
                await pyrogram_app.stop()
        except Exception as e:
            print(f"⚠️ Ошибка при остановке перед переподключением: {e}")
        
        # Пробуем запустить заново
        try:
            await pyrogram_app.start()
            print("✅ Pyrogram переподключён")
            return pyrogram_app
        except Exception as e:
            print(f"❌ Не удалось переподключиться: {e}")
            return None
    
    # Если клиент не был инициализирован
    init_pyrogram()
    if pyrogram_app:
        try:
            await pyrogram_app.start()
            print("✅ Pyrogram инициализирован и запущен")
            return pyrogram_app
        except Exception as e:
            print(f"❌ Ошибка запуска нового клиента: {e}")
            return None
    
    return None


def get_pyrogram():
    """Возвращает глобальный Pyrogram клиент"""
    return pyrogram_app
