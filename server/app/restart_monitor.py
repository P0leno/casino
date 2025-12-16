"""
Мониторинг канала логов для автоматического перезапуска
При обнаружении текста "рестарт" в канале логов - перезапускает весь сервер
"""
import os
import sys
import asyncio
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from app.config import LOG_BOT_TOKEN, LOGS_ID, DB_PATH
import logging
import signal

logger = logging.getLogger(__name__)

# Глобальные переменные для отслеживания задач
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = 'restart_message_id'")
        conn.commit()
        conn.close()
        logger.info("Cleared restart_message_id")
    except Exception as e:
        logger.error(f"Error clearing restart_message_id: {e}")


async def handle_restart_command(message: types.Message, bot: Bot):
    """Обработчик команды перезапуска с graceful shutdown"""
    global restart_in_progress
    
    if restart_in_progress:
        return
    
    restart_in_progress = True
    
    try:
        # 1. Отправляем начальное сообщение
        status_msg = await bot.send_message(
            chat_id=LOGS_ID,
            text="🔄 <b>Запущен процесс перезагрузки...</b>\n\n"
                 "⏱️ Ожидание завершения текущего раунда...\n"
                 "💾 Сохранение данных...",
            parse_mode="HTML"
        )
        message_id = status_msg.message_id
        
        # 2. Сохраняем message_id для обновления после старта
        save_restart_message_id(message_id)
        
        # 3. Делаем небольшую паузу
        await asyncio.sleep(1.0)
        
        # 4. Посылаем сигнал SIGTERM самому себе
        logger.info("📡 Sending SIGTERM to self to initiate graceful shutdown...")
        os.kill(os.getpid(), signal.SIGTERM)
        
    except Exception as e:
        logger.error(f"Error during restart sequence: {e}")
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


async def stop_restart_monitor():
    """Остановить мониторинг (ничего не делает, т.к. обработчики в log_bot)"""
    logger.info("🛑 Stopping restart monitor (handlers remain in log_bot)...")
