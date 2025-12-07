"""
Мониторинг канала логов для автоматического перезапуска
При обнаружении текста "рестарт" в канале логов - перезапускает весь сервер
"""
import os
import sys
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from app.config import LOG_BOT_TOKEN, LOGS_ID, DB_PATH
import logging

logger = logging.getLogger(__name__)

# Глобальные переменные для отслеживания задач
active_tasks = {}
restart_in_progress = False


async def send_status_to_channel(bot: Bot, message: str, message_id: int = None):
    """Отправить или обновить сообщение в канале через log_bot"""
    try:
        # Импортируем log_bot для отправки/редактирования сообщений
        from app.log_bot import log_bot
        
        if message_id:
            # Обновляем существующее сообщение
            await log_bot.edit_message_text(
                chat_id=LOGS_ID,
                message_id=message_id,
                text=message,
                parse_mode="HTML"
            )
        else:
            # Отправляем новое сообщение
            msg = await log_bot.send_message(
                chat_id=LOGS_ID,
                text=message,
                parse_mode="HTML"
            )
            return msg.message_id
    except Exception as e:
        logger.error(f"Error sending status to channel: {e}")
        return None


def save_restart_message_id(message_id: int):
    """Сохранить message_id сообщения о рестарте в БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, description)
            VALUES ('restart_message_id', ?, 'ID сообщения о последнем рестарте')
        """, (str(message_id),))
        conn.commit()
        conn.close()
        logger.info(f"Saved restart_message_id: {message_id}")
    except Exception as e:
        logger.error(f"Error saving restart_message_id: {e}")


def get_restart_message_id():
    """Получить message_id последнего рестарта"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'restart_message_id'")
        result = cursor.fetchone()
        conn.close()
        if result:
            return int(result[0])
        return None
    except Exception as e:
        logger.error(f"Error getting restart_message_id: {e}")
        return None


def clear_restart_message_id():
    """Очистить message_id после успешного старта"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = 'restart_message_id'")
        conn.commit()
        conn.close()
        logger.info("Cleared restart_message_id")
    except Exception as e:
        logger.error(f"Error clearing restart_message_id: {e}")


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
        # Сохраняем информацию о Redis до остановки задач
        try:
            from app.tasks.redis_sync import stop_redis_sync
            logger.info("💾 Сохраняю данные из Redis...")
            await stop_redis_sync()
            logger.info("✅ Redis синхронизация остановлена")
        except Exception as e:
            logger.error(f"Error stopping Redis sync: {e}")
        
        # Получаем все задачи из event loop
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.all_tasks(loop)
        
        # Исключаем текущую задачу и родительские задачи перезапуска
        current_task = asyncio.current_task()
        tasks_to_cancel = []
        
        for t in all_tasks:
            if t == current_task or t.done():
                continue
            # Пытаемся получить имя задачи
            task_name = t.get_name() if hasattr(t, 'get_name') else str(t)
            # Не отменяем задачи рестарта
            if 'restart' not in task_name.lower() and 'monitor' not in task_name.lower():
                tasks_to_cancel.append(t)
        
        logger.info(f"Cancelling {len(tasks_to_cancel)} tasks...")
        
        # Отменяем все задачи
        for task in tasks_to_cancel:
            task.cancel()
        
        # Ждём завершения всех задач (с timeout)
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning("Некоторые задачи не завершились за 3 секунды")
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
    
    # Небольшая задержка чтобы все сообщения успели отправиться
    await asyncio.sleep(0.3)
    
    # Перезапускаем процесс (os.execl заменит текущий процесс на новый)
    python = sys.executable
    logger.info(f"Executing: {python} {' '.join(sys.argv)}")
    os.execl(python, python, *sys.argv)


async def handle_restart_command(message: types.Message, bot: Bot):
    """Обработчик команды перезапуска с graceful shutdown"""
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
        
        # 2. Останавливаем новые раунды краша
        from app.crash_game import crash_game
        crash_game.shutting_down = True
        
        crash_status = ""
        if crash_game.is_running:
            crash_status = f"\n🎲 <b>Краш-игра:</b> Раунд #{crash_game.game_id} идет, ждем завершения..."
            logger.info(f"Crash game round #{crash_game.game_id} is running, waiting for completion...")
        else:
            crash_status = "\n🎲 <b>Краш-игра:</b> Раунд не идет"
        
        # 3. Собираем список активных задач
        active_tasks_list = get_active_tasks_list()
        
        tasks_text = ""
        if active_tasks_list:
            tasks_text = "\n".join([f"  • {task}" for task in active_tasks_list])
        else:
            tasks_text = "  • Нет активных задач"
        
        # 4. Обновляем сообщение со статусом краша
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"📊 <b>Активных задач: {len(active_tasks_list)}</b>\n"
            f"{tasks_text}\n"
            f"{crash_status}\n\n"
            f"⏳ Ожидаю завершения активных раундов...",
            message_id
        )
        
        # 5. Ждем завершения краш-раунда (максимум 60 сек)
        wait_time = 0
        while crash_game.is_running and wait_time < 60:
            await asyncio.sleep(1)
            wait_time += 1
            
            if wait_time % 5 == 0:  # Обновляем каждые 5 сек
                await send_status_to_channel(
                    bot,
                    f"🔄 <b>Перезапускаюсь...</b>\n\n"
                    f"🎲 <b>Краш-игра:</b> Раунд #{crash_game.game_id} все еще идет...\n"
                    f"⏳ Ожидание: {wait_time}с / 60с\n\n"
                    f"📊 После завершения раунда остановлю все задачи",
                    message_id
                )
        
        if crash_game.is_running:
            logger.warning(f"Crash game didn't finish in 60s, proceeding with shutdown anyway")
        else:
            logger.info("Crash game finished, proceeding with shutdown")
        
        # 6. Закрываем все WebSocket соединения
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"✅ Краш-раунд завершен\n"
            f"⏳ Закрываю WebSocket соединения...",
            message_id
        )
        
        try:
            from app.routers.crash import manager
            await manager.disconnect_all()
            logger.info("All WebSocket connections closed")
        except Exception as e:
            logger.error(f"Error closing WebSockets: {e}")
        
        await asyncio.sleep(0.5)
        
        # 7. Останавливаем все задачи gracefully
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"✅ WebSocket соединения закрыты\n"
            f"⏳ Останавливаю фоновые задачи...",
            message_id
        )
        
        stopped_count = await graceful_shutdown_all_tasks()
        
        # 8. Обновляем сообщение - задачи остановлены
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
        
        # 9. Финальное обновление - перезагружаемся
        await send_status_to_channel(
            bot,
            f"🔄 <b>Перезапускаюсь...</b>\n\n"
            f"✅ Все задачи остановлены ({stopped_count})\n"
            f"✅ Краш-игра завершена\n"
            f"✅ WebSocket соединения закрыты\n"
            f"🚀 Запускаю сервер заново...",
            message_id
        )
        
        # Сохраняем message_id для обновления после старта
        save_restart_message_id(message_id)
        
        await asyncio.sleep(0.5)
        
        # 10. Перезапускаем сервер
        await restart_server()
        
    except Exception as e:
        logger.error(f"Error during restart: {e}")
        await bot.send_message(
            chat_id=LOGS_ID,
            text=f"❌ <b>Ошибка при перезапуске:</b>\n{str(e)}",
            parse_mode="HTML"
        )
        restart_in_progress = False


async def setup_restart_monitor_handlers():
    """Регистрирует обработчики команд рестарта в log_router"""
    from app.log_bot import log_router
    
    @log_router.message()
    async def handle_message(message: types.Message):
        """Обработка всех сообщений в канале для команды рестарта"""
        if message.chat.id != int(LOGS_ID):
            return
        
        text = message.text or message.caption or ""
        text_lower = text.lower().strip()
        
        # Проверяем команды перезапуска
        restart_keywords = ['рестарт', 'restart', '/restart', '/рестарт', 'перезапуск']
        
        if any(keyword in text_lower for keyword in restart_keywords):
            logger.info(f"🔄 Restart command detected: {text}")
            from app.log_bot import log_bot
            await handle_restart_command(message, log_bot)
    
    logger.info("[RESTART_MONITOR] ✅ Restart monitor handlers registered")


async def start_restart_monitor():
    """Запустить мониторинг перезапуска (регистрирует обработчики в log_bot)"""
    await setup_restart_monitor_handlers()
    logger.info("✅ Restart monitor handlers attached to log_bot")


# Для совместимости
async def stop_restart_monitor():
    """Остановить мониторинг (ничего не делает, т.к. обработчики в log_bot)"""
    logger.info("🛑 Stopping restart monitor (handlers remain in log_bot)...")
