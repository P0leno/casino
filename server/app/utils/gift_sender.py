"""
Асинхронная отправка подарков через Pyrogram (pyrofork)
"""
import asyncio
from app.pyrogram_client import get_pyrogram, reconnect_pyrogram
from app.utils.error_logger import send_error_log

MAX_RETRIES = 3
RETRY_DELAY = 2  # секунды


async def send_gift_async(user_id: int, gift_id: str, pyrogram_app = None) -> tuple[bool, str, bool]:
    """
    Отправляет подарок пользователю асинхронно без логов
    
    Args:
        user_id: ID пользователя Telegram
        gift_id: ID подарка (строка или int)
        pyrogram_app: Инициализированный Pyrogram клиент (опционально)
    
    Returns:
        tuple[bool, str, bool]: (успех, текст_ошибки, is_peer_invalid)
    """
    if pyrogram_app is None:
        pyrogram_app = get_pyrogram()
    
    if pyrogram_app is None:
        print("❌ Pyrogram клиент не инициализирован")
        return (False, "Pyrogram клиент не инициализирован", False)
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            await pyrogram_app.send_gift(
                chat_id=user_id,
                gift_id=int(gift_id),
                hide_my_name=False
            )
            return (True, "", False)
        except RuntimeError as e:
            # Ошибка закрытого соединения - переподключаемся
            error_msg = str(e)
            if "closed" in error_msg.lower() or "handler is closed" in error_msg.lower():
                print(f"⚠️ TCPTransport closed (попытка {attempt + 1}/{MAX_RETRIES}), переподключение...")
                last_error = e
                
                # Пытаемся переподключиться
                try:
                    pyrogram_app = await reconnect_pyrogram()
                    if pyrogram_app is None:
                        break
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                except Exception as reconnect_error:
                    print(f"❌ Ошибка переподключения: {reconnect_error}")
                    break
            else:
                # Другая RuntimeError - не пытаемся повторить
                last_error = e
                break
        except Exception as e:
            last_error = e
            break
    
    # Обработка финальной ошибки
    if last_error:
        error_name = type(last_error).__name__
        error_msg = str(last_error)
        is_peer_invalid = error_name == "PeerIdInvalid"
        print(f"{error_name} sending gift {gift_id} to {user_id}: {last_error}")
        await send_error_log(last_error, f"gift_sender.py: send_gift_async ({error_name})")
        return (False, f"{error_name}: {error_msg}", is_peer_invalid)
    
    return (False, "Неизвестная ошибка", False)


async def send_multiple_gifts(gifts: list[tuple[int, str]], pyrogram_app = None) -> dict:
    """
    Отправляет несколько подарков параллельно
    
    Args:
        gifts: Список кортежей (user_id, gift_id)
        pyrogram_app: Pyrogram клиент (опционально)
    
    Returns:
        dict: {"success": int, "failed": int}
    """
    tasks = [send_gift_async(user_id, gift_id, pyrogram_app) for user_id, gift_id in gifts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success = sum(1 for r in results if isinstance(r, tuple) and r[0] is True)
    failed = len(results) - success
    
    return {"success": success, "failed": failed}
