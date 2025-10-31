"""
Асинхронная отправка подарков через Pyrogram (pyrofork)
"""
import asyncio
from app.pyrogram_client import get_pyrogram

async def send_gift_async(user_id: int, gift_id: str, pyrogram_app = None) -> tuple[bool, str]:
    """
    Отправляет подарок пользователю асинхронно без логов
    
    Args:
        user_id: ID пользователя Telegram
        gift_id: ID подарка (строка или int)
        pyrogram_app: Инициализированный Pyrogram клиент (опционально)
    
    Returns:
        tuple[bool, str]: (успех, текст_ошибки)
    """
    if pyrogram_app is None:
        pyrogram_app = get_pyrogram()
    
    if pyrogram_app is None:
        print("❌ Pyrogram клиент не инициализирован")
        return (False, "Pyrogram клиент не инициализирован")
    
    try:
        await pyrogram_app.send_gift(
            chat_id=user_id,
            gift_id=int(gift_id),
            hide_my_name=False
        )
        return (True, "")
    except Exception as e:
        error_name = type(e).__name__
        error_msg = str(e)
        print(f"{error_name} sending gift {gift_id} to {user_id}: {e}")
        return (False, f"{error_name}: {error_msg}")


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
