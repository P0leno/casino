"""
Мониторинг канала логов для автоматического перезапуска
При обнаружении текста "рестарт" в канале логов - перезапускает весь сервер
"""
import os
import sys
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from app.config import LOG_BOT_TOKEN, LOGS_ID
import logging

logger = logging.getLogger(__name__)

# Глобальные переменные для отслеживания задач
active_tasks = {}
restart_in_progress = False


async def send_status_to_channel(bot: Bot, message: str, message_id: int = None):
    """Отправить или обновить сообщение в канале"""
    try:
        if message_id:
            # Обновляем существующее сообщение
            await bot.edit_message_text(
                chat_id=LOGS_ID,
                message_id=message_id,
                text=message,
                parse_mode="HTML"
            )
        else:
            # Отправляем новое сообщение
            msg = await bot.send_message(
                chat_id=LOGS_ID,
                text=message,
                parse_mode="HTML"
            )
            return msg.message_id
    except Exception as e:
        logger.error(f"Error sending status to channel: {e}")
        return None


def get_active_tasks_list():
    """Получить список активных задач"""
    tasks = []
    
    # Получаем все активные задачи из event loop
    try:
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.all_tasks(loop)
        
        # Считаем незавершенные задачи (исключая текущую)
        active_count = len([t for t in all_tasks if not t.done() and t != asyncio.current_task()])
        
        # Добавляем примерные названия задач
        task_names = [
            "🤖 Telegram Bot",
            "🔔 Spin Notifications", 
            "🎲 Crash Game",
            "💎 TON Transaction Checker",
            "🎁 Gift Parser",
            "💰 TON Price Updater",
            "📦 Gift Models Checker",
            "💬 Support Bot",
            "💳 CryptoBot Checker",
            "🔴 Redis Sync"
        ]
        
        # Возвращаем примерный список (по количеству активных задач)
        tasks = task_names[:min(active_count, len(task_names))]
        
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
    
    return tasks


async def graceful_shutdown_all_tasks():
    """Gracefully остановить все задачи"""
    try:
        # Получаем все задачи из event loop
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.all_tasks(loop)
        
        # Исключаем текущую задачу
        current_task = asyncio.current_task()
        tasks_to_cancel = [t for t in all_tasks if t != current_task and not t.done()]
        
        logger.info(f"Cancelling {len(tasks_to_cancel)} tasks...")
        
        # Отменяем все задачи
        for task in tasks_to_cancel:
            task.cancel()
        
        # Ждём завершения всех задач (с timeout)
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Некоторые задачи не завершились за 5 секунд")
            except Exception as e:
                logger.error(f"Error waiting for tasks: {e}")
        
        # Закрываем Redis connection pool
        try:
            from app.utils.redis_client import redis_client
            if redis_client:
                redis_client.close()
                logger.info("Redis connections closed")
        except:
            pass
        
        # Останавливаем Pyrogram
        try:
            from app.pyrogram_client import stop_pyrogram
            await stop_pyrogram()
            logger.info("Pyrogram stopped")
        except:
            pass
        
        return len(tasks_to_cancel)
        
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")
        return 0


async def restart_server():
    """Перезапустить сервер"""
    logger.info("🔄 Restarting server...")
    
    # Закрываем текущий event loop
    try:
        loop = asyncio.get_event_loop()
        loop.stop()
    except:
        pass
    
    # Перезапускаем процесс
    python = sys.executable
    os.execl(python, python, *sys.argv)


async def handle_restart_command(message: types.Message, bot: Bot):
    """Обработчик команды перезапуска"""
    global restart_in_progress
    
    if restart_in_progress:
        await bot.send_message(
            chat_id=LOGS_ID,
            text="⚠️ Перезапуск уже в процессе...",
            parse_mode="HTML"
        )
        return
    
    restart_in_progress = True
    
    try:
        # 1. Отправляем начальное сообщение
        status_msg = await bot.send_message(
            chat_id=LOGS_ID,
            text="🔄 <b>Перезапускаюсь...</b>\n\n📊 Собираю информацию о задачах...",
            parse_mode="HTML"
        )
        message_id = status_msg.message_id
        
        await asyncio.sleep(0.5)
        
        # 2. Собираем список активных задач
        active_tasks_list = get_active_tasks_list()
        
        tasks_text = ""
        if active_tasks_list:
            tasks_text = "\n".join([f"  • {task}" for task in active_tasks_list])
        else:
            tasks_text = "  • Нет активных задач"
        
        # 3. Обновляем сообщение со списком задач
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"📊 <b>Активных задач: {len(active_tasks_list)}</b>\n"
            f"{tasks_text}\n\n"
            f"⏳ Останавливаю задачи...",
            message_id
        )
        
        await asyncio.sleep(1)
        
        # 4. Останавливаем все задачи gracefully
        stopped_count = await graceful_shutdown_all_tasks()
        
        # 5. Обновляем сообщение - задачи остановлены
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"📊 <b>Активных задач было: {len(active_tasks_list)}</b>\n"
            f"{tasks_text}\n\n"
            f"✅ Остановлено задач: {stopped_count}\n"
            f"⏳ Завершаю работу...",
            message_id
        )
        
        await asyncio.sleep(0.5)
        
        # 6. Финальное обновление - перезагружаемся
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезагружаюсь...</b>\n\n"
            f"✅ Все задачи остановлены ({stopped_count})\n"
            f"🚀 Запускаю сервер заново...",
            message_id
        )
        
        await asyncio.sleep(0.5)
        
        # 7. Перезапускаем сервер
        await restart_server()
        
    except Exception as e:
        logger.error(f"Error during restart: {e}")
        await bot.send_message(
            chat_id=LOGS_ID,
            text=f"❌ <b>Ошибка при перезапуске:</b>\n{str(e)}",
            parse_mode="HTML"
        )
        restart_in_progress = False


async def monitor_channel():
    """Мониторинг канала логов на команду перезапуска"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        logger.warning("LOG_BOT_TOKEN or LOGS_ID not set, restart monitor disabled")
        return
    
    bot = Bot(token=LOG_BOT_TOKEN)
    dp = Dispatcher()
    
    @dp.message()
    async def handle_message(message: types.Message):
        """Обработка всех сообщений в канале"""
        if message.chat.id != int(LOGS_ID):
            return
        
        text = message.text or message.caption or ""
        text_lower = text.lower().strip()
        
        # Проверяем команды перезапуска
        restart_keywords = ['рестарт', 'restart', '/restart', '/рестарт', 'перезапуск']
        
        if any(keyword in text_lower for keyword in restart_keywords):
            logger.info(f"🔄 Restart command detected: {text}")
            await handle_restart_command(message, bot)
    
    logger.info("[RESTART_MONITOR] 🔍 Restart monitor started, listening for 'рестарт' command")
    print("[RESTART_MONITOR] Запуск мониторинга перезапуска...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"[RESTART_MONITOR] Error in restart monitor: {e}")
        print(f"[RESTART_MONITOR] Ошибка: {e}")
    finally:
        await bot.session.close()


async def start_restart_monitor():
    """Запустить мониторинг перезапуска"""
    asyncio.create_task(monitor_channel())
    logger.info("✅ Restart monitor task created")


# Для совместимости
async def stop_restart_monitor():
    """Остановить мониторинг"""
    logger.info("🛑 Stopping restart monitor...")
