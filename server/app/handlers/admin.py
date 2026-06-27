import json
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import ADMIN_IDS
from app.utils.error_logger import send_error_log
from app.utils.database import get_db_connection

router = Router()

APP_URL = "https://proxmox-bubuntu1.tailcfe40a.ts.net"


def save_admins_to_db(admin_ids: list[int]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES ('admins', ?, 'Список ID администраторов', CURRENT_TIMESTAMP)",
        (json.dumps(admin_ids),)
    )
    conn.commit()
    conn.close()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть панель", web_app=WebAppInfo(url=APP_URL))],
        [InlineKeyboardButton(text="🔄 Парсинг подарков", callback_data="force_gift_parse")],
        [InlineKeyboardButton(text="👥 Админы", callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="admin_balance_menu")],
        [InlineKeyboardButton(text="📝 Причина закрытия", callback_data="admin_maintenance_reason")],
        [InlineKeyboardButton(text="🚧 Перезапустить сервер", callback_data="admin_restart")],
        [InlineKeyboardButton(text="⏻ Тех.работы", callback_data="admin_toggle_maintenance")],
    ])

    await message.answer(
        "👋 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin_list_admins")
async def admin_list_admins_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    lines = [f"👥 <b>Администраторы ({len(ADMIN_IDS)})</b>\n"]
    for uid in ADMIN_IDS:
        lines.append(f"  • <code>{uid}</code>")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_balance_menu")
async def admin_balance_menu_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
    ])

    await callback.message.edit_text(
        "💰 <b>Управление балансом</b>\n\n"
        "Используйте веб-панель для управления.\n"
        "В админке веб-панели доступны:\n"
        "• Пополнение / списание баланса\n"
        "• Выдача подарков\n"
        "• Информация о пользователе",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть панель", web_app=WebAppInfo(url=APP_URL))],
        [InlineKeyboardButton(text="🔄 Парсинг подарков", callback_data="force_gift_parse")],
        [InlineKeyboardButton(text="👥 Админы", callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="admin_balance_menu")],
        [InlineKeyboardButton(text="📝 Причина закрытия", callback_data="admin_maintenance_reason")],
        [InlineKeyboardButton(text="🚧 Перезапустить сервер", callback_data="admin_restart")],
        [InlineKeyboardButton(text="⏻ Тех.работы", callback_data="admin_toggle_maintenance")],
    ])

    await callback.message.edit_text(
        "👋 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "admin_maintenance_reason")
async def admin_maintenance_reason_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_reason'")
    row = cursor.fetchone()
    current_reason = row[0] if row else "Сервер временно недоступен"
    conn.close()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
    ])

    await callback.message.edit_text(
        "📝 <b>Причина закрытия</b>\n\n"
        "Текущая причина:\n"
        f"<i>{current_reason}</i>\n\n"
        "Изменить — используйте веб-панель.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
    result = cursor.fetchone()
    current = result[0] if result else '0'
    new_value = '0' if current == '1' else '1'
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", (new_value,))
    conn.commit()
    conn.close()

    status = "включён" if new_value == '1' else "выключен"
    await callback.answer(f"✅ Режим техработ {status}", show_alert=True)
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Режим технических работ <b>{status}</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("download_models:"))
async def download_models_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    try:
        gift_name = callback.data.split(":", 1)[1]
        await callback.answer(f"📥 Начинаю загрузку моделей для {gift_name}...")

        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ <i>Загружаю модели...</i> [0/0]",
            parse_mode="HTML"
        )

        from app.tasks.gift_models_checker import download_gift_models, MODELS_DIR
        success = await download_gift_models(gift_name, message_to_edit=callback.message)

        import os
        gift_folder = os.path.join(MODELS_DIR, gift_name)
        models_count = 0
        if os.path.exists(gift_folder):
            models_count = len([f for f in os.listdir(gift_folder) if f.endswith(".json")])

        original_text = callback.message.text.split('\n\n⏳')[0].strip()

        if success:
            await callback.message.edit_text(
                f"{original_text}\n\n✅ <b>Модели загружены [{models_count}/{models_count}]</b>\n📄 Файл models_list.json обновлен",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"{original_text}\n\n⚠️ <b>Загрузка завершена с ошибками</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error in download_models_handler: {e}")
        await send_error_log(e, "admin.py: download_models_handler")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@router.callback_query(F.data.startswith("decline_models:"))
async def decline_models_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    try:
        gift_name = callback.data.split(":", 1)[1]
        await callback.answer(f"❌ Загрузка отклонена для {gift_name}")
        await callback.message.delete()
    except Exception as e:
        print(f"Error in decline_models_handler: {e}")
        await send_error_log(e, "admin.py: decline_models_handler")


@router.callback_query(F.data == "force_gift_parse")
async def force_gift_parse_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return

    try:
        await callback.answer("🔄 Запущен принудительный парсинг...")

        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ <i>Выполняется принудительный парсинг...</i>",
            parse_mode="HTML"
        )

        from app.tasks.gift_parser import force_parse_and_sync
        from app.tasks.price_updater import search_tonnel_resale, update_gift_ton_price
        import app.tasks.gift_parser as gift_parser_module

        result = await force_parse_and_sync(search_tonnel_resale, update_gift_ton_price)
        gift_parser_module.last_full_sync_time = asyncio.get_event_loop().time()

        await callback.message.edit_text(
            f"{callback.message.text.split('⏳')[0].strip()}\n\n"
            f"✅ <b>Принудительное обновление цен завершено</b>\n\n"
            f"Обновлено цен в TON: <b>{result['prices_updated']}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error in force_gift_parse_handler: {e}")
        await send_error_log(e, "admin.py: force_gift_parse_handler")
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
    try:
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("Ошибка: неверный формат данных")
            return

        await callback.message.delete()
        await callback.answer("✅ Запрос подтвержден и удален")
    except Exception as e:
        print(f"Error in confirm_gift_handler: {e}")
        await send_error_log(e, "admin.py: confirm_gift_handler")
        await callback.answer("Ошибка при обработке")
