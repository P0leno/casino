from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import asyncio
from app.config import ADMIN_IDS
from app.utils.error_logger import send_error_log

router = Router()

APP_URL = "https://proxmox-bubuntu1.tailcfe40a.ts.net"


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть панель", web_app=WebAppInfo(url=APP_URL))],
        [InlineKeyboardButton(text="🔄 Парсинг подарков", callback_data="force_gift_parse")],
        [InlineKeyboardButton(text="🚧 Перезапустить сервер", callback_data="admin_restart")],
        [InlineKeyboardButton(text="⏻ Вкл/Выкл тех.работы", callback_data="admin_toggle_maintenance")],
    ])

    await message.answer(
        "👋 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin_restart")
async def admin_restart_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    await callback.answer("🔄 Перезапуск...", show_alert=False)
    await callback.message.edit_text("🔄 <b>Перезапуск сервера...</b>", parse_mode="HTML")

    from app.restart_monitor import handle_restart_command
    from app.bot import bot
    asyncio.create_task(handle_restart_command(None, bot))


@router.callback_query(F.data == "admin_toggle_maintenance")
async def admin_toggle_maintenance_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    from app.utils.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
    result = cursor.fetchone()
    current = result[0] if result else '0'
    new_value = '0' if current == '1' else '1'
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", (new_value,))
    conn.commit()
    conn.close()

    status = "включен" if new_value == '1' else "выключен"
    await callback.answer(f"✅ Режим техработ {status}", show_alert=True)
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Режим технических работ <b>{status}</b>",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("download_models:"))
async def download_models_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Принять' для загрузки моделей подарка"""
    try:
        # Проверяем что пользователь - админ
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Извлекаем название подарка
        gift_name = callback.data.split(":", 1)[1]
        
        # Отвечаем что начали обработку
        await callback.answer(f"📥 Начинаю загрузку моделей для {gift_name}...")
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ <i>Загружаю модели...</i> [0/0]",
            parse_mode="HTML"
        )
        
        # Загружаем модели с прогрессом
        from app.tasks.gift_models_checker import download_gift_models
        success = await download_gift_models(gift_name, message_to_edit=callback.message)
        
        # Получаем количество загруженных моделей
        from app.tasks.gift_models_checker import MODELS_DIR
        import os
        gift_folder = os.path.join(MODELS_DIR, gift_name)
        models_count = 0
        if os.path.exists(gift_folder):
            models_count = len([f for f in os.listdir(gift_folder) if f.endswith(".json")])
        
        # Обновляем сообщение с результатом
        original_text = callback.message.text.split('\n\n⏳')[0].strip()
        
        if success:
            result_text = f"{original_text}\n\n"
            result_text += f"✅ <b>Модели загружены [{models_count}/{models_count}]</b>\n"
            result_text += f"📄 Файл models_list.json обновлен"
            await callback.message.edit_text(result_text, parse_mode="HTML")
        else:
            result_text = f"{original_text}\n\n"
            result_text += f"⚠️ <b>Загрузка завершена с ошибками</b>"
            await callback.message.edit_text(result_text, parse_mode="HTML")
        
    except Exception as e:
        print(f"Error in download_models_handler: {e}")
        await send_error_log(e, "admin.py: download_models_handler")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка загрузки", show_alert=True)

@router.callback_query(F.data.startswith("decline_models:"))
async def decline_models_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Отклонить' - удаляет сообщение"""
    try:
        # Проверяем что пользователь - админ
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Извлекаем название подарка
        gift_name = callback.data.split(":", 1)[1]
        
        await callback.answer(f"❌ Загрузка отклонена для {gift_name}")
        
        # Удаляем сообщение
        await callback.message.delete()
        
    except Exception as e:
        print(f"Error in decline_models_handler: {e}")
        await send_error_log(e, "admin.py: decline_models_handler")
        import traceback
        traceback.print_exc()


@router.callback_query(F.data == "force_gift_parse")
async def force_gift_parse_handler(callback: CallbackQuery):
    """Обработчик принудительного парсинга подарков"""
    try:
        # Проверяем что пользователь - админ
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Отвечаем что начали обработку
        await callback.answer("🔄 Запущен принудительный парсинг...")
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ <i>Выполняется принудительный парсинг...</i>",
            parse_mode="HTML"
        )
        
        # Импортируем функции парсинга
        from app.tasks.gift_parser import force_parse_and_sync, last_full_sync_time
        from app.tasks.price_updater import search_tonnel_resale, update_gift_ton_price
        import app.tasks.gift_parser as gift_parser_module
        
        # Выполняем принудительный парсинг и синхронизацию
        result = await force_parse_and_sync(search_tonnel_resale, update_gift_ton_price)
        
        # Сбрасываем таймер автономной синхронизации
        gift_parser_module.last_full_sync_time = asyncio.get_event_loop().time()
        print(f"⏰ Таймер автономной синхронизации сброшен")
        
        # Обновляем сообщение с результатом
        result_text = f"{callback.message.text.split('⏳')[0].strip()}\n\n"
        result_text += f"✅ <b>Принудительное обновление цен завершено</b>\n\n"
        result_text += f"Обновлено цен в TON: <b>{result['prices_updated']}</b>"
        
        await callback.message.edit_text(result_text, parse_mode="HTML")
        
    except Exception as e:
        print(f"Error in force_gift_parse_handler: {e}")
        await send_error_log(e, "admin.py: force_gift_parse_handler")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при парсинге", show_alert=True)
        try:
            await callback.message.edit_text(
                f"{callback.message.text.split('⏳')[0].strip()}\n\n❌ <i>Ошибка: {str(e)}</i>",
                parse_mode="HTML"
            )
        except:
            pass

@router.callback_query(F.data.startswith("confirm_gift_"))
async def confirm_gift_handler(callback: CallbackQuery):
    """Обработчик подтверждения ручной выдачи подарка"""
    try:
        # Парсим callback_data: confirm_gift_{user_id}_{gift_id}
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        user_id = parts[2]
        gift_id = parts[3]
        
        # Удаляем сообщение
        await callback.message.delete()
        
        # Подтверждаем действие
        await callback.answer("✅ Запрос подтвержден и удален")
        
    except Exception as e:
        print(f"Error in confirm_gift_handler: {e}")
        await send_error_log(e, "admin.py: confirm_gift_handler")
        await callback.answer("Ошибка при обработке")
