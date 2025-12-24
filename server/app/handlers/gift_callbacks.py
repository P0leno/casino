"""
Обработчики callback кнопок для повторной отправки подарков
"""
from aiogram import Router, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import json

from app.config import BOT_TOKEN, LOG_BOT_TOKEN, LOGS_ID
from app.utils.database import get_db_connection
from app.utils.gift_sender import send_gift_async
from app.pyrogram_client import get_pyrogram
from app.utils.error_logger import send_error_log
from app.utils.redis_client import cache

router = Router()

@router.callback_query(lambda c: c.data and c.data.startswith("retry_gift:"))
async def retry_gift_callback(callback: CallbackQuery):
    """Обработка кнопки 'Попробовать ещё раз'"""
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("Ошибка данных", show_alert=True)
            return
        
        user_id = int(parts[1])
        gift_name = parts[2]
        
        # Проверяем что это тот же пользователь
        if callback.from_user.id != user_id:
            await callback.answer("Это не ваша кнопка", show_alert=True)
            return
        
        # Rate limit: 1 раз в минуту
        rate_key = f"retry_gift_rate:{user_id}"
        if cache.is_available():
            if cache.client.get(rate_key):
                ttl = cache.client.ttl(rate_key)
                await callback.answer(f"⏳ Подождите {ttl} сек.", show_alert=True)
                return
            # Устанавливаем блокировку на 60 секунд
            cache.client.setex(rate_key, 60, "1")
        
        await callback.answer("⏳ Проверяю подарок...")
        
        # Проверяем наличие подарка в инвентаре
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            await callback.message.edit_text("❌ Пользователь не найден")
            return
        
        inventory = json.loads(result[0]) if result[0] else []
        
        if gift_name not in inventory:
            conn.close()
            await callback.message.edit_text(
                "❌ <b>Подарок не найден в инвентаре</b>\n\n"
                "Возможно, он уже был отправлен или удалён.",
                parse_mode="HTML"
            )
            return
        
        # Получаем gift_id
        cursor.execute("SELECT gift_id FROM gift_prices WHERE gift_name = ?", (gift_name,))
        gift_result = cursor.fetchone()
        
        if not gift_result or not gift_result[0]:
            conn.close()
            await callback.message.edit_text("❌ Gift ID не найден")
            return
        
        gift_id = gift_result[0]
        
        # Удаляем подарок из инвентаря
        inventory.remove(gift_name)
        cursor.execute(
            "UPDATE users SET inventory = ? WHERE id = ?",
            (json.dumps(inventory), user_id)
        )
        conn.commit()
        
        # Пробуем отправить
        pyrogram_app = get_pyrogram()
        send_success, error_msg, is_peer_invalid = await send_gift_async(user_id, gift_id, pyrogram_app)
        
        if send_success:
            conn.close()
            await callback.message.edit_text(
                "✅ <b>Подарок успешно отправлен!</b>\n\n"
                f"🎁 {gift_name}",
                parse_mode="HTML"
            )
        else:
            # Возвращаем подарок в инвентарь
            inventory.append(gift_name)
            cursor.execute(
                "UPDATE users SET inventory = ? WHERE id = ?",
                (json.dumps(inventory), user_id)
            )
            conn.commit()
            conn.close()
            
            # Показываем сообщение с кнопками
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Попробовать ещё раз", callback_data=f"retry_gift:{user_id}:{gift_name}"),
                    InlineKeyboardButton(text="❓ Помощь", callback_data=f"help_gift:{user_id}:{gift_name}")
                ]
            ])
            await callback.message.edit_text(
                "❌ <b>Снова не удалось отправить подарок</b>\n\n"
                "Убедитесь, что вы начали чат с ботом @shellrelayer\n\n"
                f"🎁 Подарок: <b>{gift_name}</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        print(f"Error in retry_gift_callback: {e}")
        await send_error_log(e, "gift_callbacks.py: retry_gift_callback")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("help_gift:"))
async def help_gift_callback(callback: CallbackQuery):
    """Обработка кнопки 'Помощь' - отправка запроса администраторам"""
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("Ошибка данных", show_alert=True)
            return
        
        user_id = int(parts[1])
        gift_name = parts[2]
        
        # Проверяем что это тот же пользователь
        if callback.from_user.id != user_id:
            await callback.answer("Это не ваша кнопка", show_alert=True)
            return
        
        # Rate limit: 1 раз в минуту
        rate_key = f"help_gift_rate:{user_id}"
        if cache.is_available():
            if cache.client.get(rate_key):
                ttl = cache.client.ttl(rate_key)
                await callback.answer(f"⏳ Подождите {ttl} сек.", show_alert=True)
                return
            # Устанавливаем блокировку на 60 секунд
            cache.client.setex(rate_key, 60, "1")
        
        # Проверяем username
        username = callback.from_user.username
        if not username:
            await callback.answer(
                "⚠️ У вас не установлен username!\n"
                "Установите его в настройках Telegram",
                show_alert=True
            )
            return
        
        await callback.answer("Уже отправляю...")
        
        # Защита от двойной отправки заявки
        help_lock_key = f"help_request:{user_id}:{gift_name}"
        if cache.is_available():
            if cache.client.get(help_lock_key):
                await callback.answer("ℹ️ Заявка уже отправлена, ожидайте", show_alert=True)
                return
            # Устанавливаем блокировку на 30 минут (пока админ не обработает)
            cache.client.setex(help_lock_key, 1800, "1")
        
        # Проверяем наличие подарка в инвентаре
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            await callback.message.edit_text("❌ Пользователь не найден")
            return
        
        inventory = json.loads(result[0]) if result[0] else []
        
        if gift_name not in inventory:
            conn.close()
            await callback.message.edit_text(
                "❌ <b>Подарок не найден в инвентаре</b>\n\n"
                "Возможно, он уже был отправлен или удалён.",
                parse_mode="HTML"
            )
            return
        
        conn.close()
        
        # Отправляем запрос в канал логов
        if not LOG_BOT_TOKEN or not LOGS_ID:
            await callback.message.edit_text(
                "⚠️ <b>Функция помощи временно недоступна</b>\n\n"
                "Обратитесь к администратору напрямую.",
                parse_mode="HTML"
            )
            return
        
        log_bot = Bot(token=LOG_BOT_TOKEN)
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить выдачу",
                callback_data=f"admin_confirm_gift:{user_id}:{gift_name}"
            )]
        ])
        
        await log_bot.send_message(
            chat_id=LOGS_ID,
            text=(
                "🆘 <b>Запрос на ручную выдачу подарка</b>\n\n"
                f"👤 Пользователь: @{username} (ID: <code>{user_id}</code>)\n"
                f"🎁 Подарок: <b>{gift_name}</b>\n\n"
                "Нажмите кнопку для подтверждения выдачи."
            ),
            parse_mode="HTML",
            reply_markup=admin_keyboard
        )
        await log_bot.session.close()
        
        # Обновляем сообщение пользователю
        await callback.message.edit_text(
            "✅ <b>Запрос отправлен администрации!</b>\n\n"
            f"🎁 Подарок: <b>{gift_name}</b>\n\n"
            "Ожидайте — администратор скоро обработает ваш запрос.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Error in help_gift_callback: {e}")
        await send_error_log(e, "gift_callbacks.py: help_gift_callback")
        await callback.answer("Произошла ошибка", show_alert=True)
