"""
Асинхронная отправка подарков через Pyrogram (pyrofork)
"""
import asyncio
from app.pyrogram_client import get_pyrogram, reconnect_pyrogram
from app.utils.error_logger import send_error_log

from app.utils.redis_models import RedisSettings
from app.utils.database import get_db_connection

MAX_RETRIES = 3
RETRY_DELAY = 2  # секунды


async def handle_critical_error(error: Exception):
    """
    Обработка критических ошибок (например, нехватка баланса)
    Отключает авто-выдачу и пишет в логи
    """
    error_msg = str(error).lower()
    if "balance_too_low" in error_msg or "balance" in error_msg:
        print("🚨 CRITICAL: Balance too low! Disabling auto-withdrawals...")
        
        # Отключаем авто-выдачу в Redis и БД
        RedisSettings.set('withdraw_regular_enabled', '0')
        RedisSettings.set('withdraw_nft_enabled', '0')
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET value = '0' WHERE key IN ('withdraw_regular_enabled', 'withdraw_nft_enabled')")
            conn.commit()
        except Exception as db_e:
            print(f"❌ Failed to update settings in DB: {db_e}")
        finally:
            conn.close()
            
        await send_error_log(error, "CRITICAL: Auto-withdraw disabled due to low balance")


async def transfer_nft_gift_async(user_id: int, message_id: int, pyrogram_app=None) -> tuple[bool, str, bool]:
    """
    Передает NFT подарок (Unique Gift) пользователю
    
    Args:
        user_id: ID получателя
        message_id: ID сообщения с подарком (в аккаунте бота)
        pyrogram_app: Клиент
        
    Returns:
        tuple[bool, str, bool]: (success, error_msg, is_peer_invalid)
    """
    if pyrogram_app is None:
        pyrogram_app = get_pyrogram()
        
    if pyrogram_app is None:
        return (False, "Bot client not initialized", False)
        
    # 1. Resolve Peer (fix for PeerIdInvalid)
    try:
        # Пытаемся получить пользователя чтобы закэшировать access_hash
        await pyrogram_app.get_users(user_id)
    except Exception as e:
        print(f"⚠️ Could not resolve user {user_id}: {e}")
        # Продолжаем, вдруг получится
        
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            await pyrogram_app.transfer_gift(
                str(message_id),
                int(user_id)
            )
            return (True, "", False)
            
        except RuntimeError as e:
            # Reconnect logic (same as send_gift)
            error_msg = str(e)
            if "closed" in error_msg.lower() or "handler is closed" in error_msg.lower():
                print(f"⚠️ TCPTransport closed (attempt {attempt + 1}), reconnecting...")
                try:
                    pyrogram_app = await reconnect_pyrogram()
                    if not pyrogram_app: break
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                except:
                    break
            last_error = e
            break
        except AttributeError as e:
            # WORKAROUND: Library error 'object has no attribute auction_acquired' 
            # happens AFTER successful transfer when parsing update. Treat as success.
            if "auction_acquired" in str(e):
                print(f"✅ NFT Transfer successful (caught library AttributeError: {e})")
                return (True, "", False)
            last_error = e
            break

        except Exception as e:
            last_error = e
            # Проверяем на критическую ошибку баланса
            await handle_critical_error(e)
            break
            
    if last_error:
        error_name = type(last_error).__name__
        error_str = str(last_error)
        is_peer_invalid = "PEER_ID_INVALID" in error_str or error_name == "PeerIdInvalid"
        
        print(f"❌ Error transferring NFT {message_id} to {user_id}: {last_error}")
        # await send_error_log(last_error, f"gift_sender.py: transfer_nft_gift_async ({error_name})")  <-- user requested silence
        
        return (False, f"{error_name}: {error_str}", is_peer_invalid)
        
    return (False, "Unknown error", False)


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
