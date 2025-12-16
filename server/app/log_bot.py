"""
Бот для отправки логов и обработки callback в канале логов
"""
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import CallbackQuery
from app.config import LOG_BOT_TOKEN, ADMIN_IDS

log_bot = Bot(token=LOG_BOT_TOKEN)
log_dp = Dispatcher()

# Создаем отдельный router для log_bot
log_router = Router()

# Обработчики callback для кнопок в логах (копия из admin_handlers)
@log_router.callback_query(F.data.startswith("download_models:"))
async def download_models_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Принять' для загрузки моделей подарка"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
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
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка загрузки", show_alert=True)

@log_router.callback_query(F.data.startswith("decline_models:"))
async def decline_models_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Отклонить' - удаляет сообщение"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        gift_name = callback.data.split(":", 1)[1]
        await callback.answer(f"❌ Загрузка отклонена для {gift_name}")
        await callback.message.delete()
        
    except Exception as e:
        print(f"Error in decline_models_handler: {e}")
        import traceback
        traceback.print_exc()

@log_router.callback_query(F.data.startswith("af_ban_"))
async def antifraud_ban_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Заблокировать всех' (антифрод)"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Формат: af_ban_IP_id1,id2,id3
        parts = callback.data.split("_", 3)
        ip = parts[2]
        user_ids = [int(uid) for uid in parts[3].split(",")]
        
        from app.tasks.antifraud import ban_users
        ban_users(user_ids)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>Пользователи заблокированы</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Пользователи заблокированы")
        
    except Exception as e:
        print(f"Error in antifraud_ban_handler: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@log_router.callback_query(F.data.startswith("af_ignore_"))
async def antifraud_ignore_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Игнорировать' (антифрод)"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Формат: af_ignore_IP_id1,id2,id3
        parts = callback.data.split("_", 3)
        ip = parts[2]
        user_ids = [int(uid) for uid in parts[3].split(",")]
        
        from app.tasks.antifraud import ignore_ip_users
        ignore_ip_users(ip, user_ids)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>Добавлено в игнорируемые</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Добавлено в игнорируемые")
        
    except Exception as e:
        print(f"Error in antifraud_ignore_handler: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@log_router.callback_query(F.data.startswith("af_unban_"))
async def antifraud_unban_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Разбанить всех' (антифрод)"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        # Формат: af_unban_id1,id2,id3
        parts = callback.data.split("_", 2)
        user_ids = [int(uid) for uid in parts[2].split(",")]
        
        from app.tasks.antifraud import unban_users
        unban_users(user_ids)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>Пользователи разбанены</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Пользователи разбанены")
        
    except Exception as e:
        print(f"Error in antifraud_unban_handler: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@log_router.callback_query(F.data == "force_gift_parse")
async def force_gift_parse_handler(callback: CallbackQuery):
    """Обработчик принудительного парсинга подарков"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("🔄 Запущен принудительный парсинг...")
        
        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ <i>Выполняется принудительный парсинг...</i>",
            parse_mode="HTML"
        )
        
        from app.tasks.gift_parser import force_parse_and_sync, last_full_sync_time
        from app.tasks.price_updater import search_tonnel_resale, update_gift_ton_price
        import app.tasks.gift_parser as gift_parser_module
        
        result = await force_parse_and_sync(search_tonnel_resale, update_gift_ton_price)
        
        gift_parser_module.last_full_sync_time = asyncio.get_event_loop().time()
        print(f"⏰ Таймер автономной синхронизации сброшен")
        
        result_text = f"{callback.message.text.split('⏳')[0].strip()}\n\n"
        result_text += f"✅ <b>Принудительное обновление цен завершено</b>\n\n"
        result_text += f"Обновлено цен в TON: <b>{result['prices_updated']}</b>"
        
        await callback.message.edit_text(result_text, parse_mode="HTML")
        
    except Exception as e:
        print(f"Error in force_gift_parse_handler: {e}")
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

@log_router.callback_query(F.data.startswith("manual_done_"))
async def manual_withdraw_done_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Выполнен' для ручного вывода обычного подарка"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("✅ Отмечено как выполненное")
        
        # Удаляем сообщение
        await callback.message.delete()
        
    except Exception as e:
        print(f"Error in manual_withdraw_done_handler: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@log_router.callback_query(F.data.startswith("manual_nft_done_"))
async def manual_nft_withdraw_done_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Выполнен' для ручного вывода NFT подарка"""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("⛔ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("✅ NFT отмечен как выполненный")
        
        # Удаляем сообщение
        await callback.message.delete()
        
    except Exception as e:
        print(f"Error in manual_nft_withdraw_done_handler: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

# Подключаем router к dispatcher
log_dp.include_router(log_router)

async def start_log_bot():
    """Запускает log_bot для обработки callback в канале логов"""
    try:
        print("[LOG_BOT] Запуск бота логов для обработки callback...")
        await log_dp.start_polling(log_bot, allowed_updates=["callback_query"])
    except Exception as e:
        print(f"[LOG_BOT] Ошибка: {e}")
        raise

async def stop_log_bot():
    """Останавливает log_bot"""
    try:
        print("[LOG_BOT] Остановка бота логов...")
        await log_bot.session.close()
    except Exception as e:
        print(f"[LOG_BOT] Ошибка остановки: {e}")

async def send_message_to_logs(text: str, parse_mode: str = "HTML", reply_markup=None):
    """Отправляет сообщение в канал логов"""
    from app.config import LOGS_ID
    try:
        if reply_markup:
            return await log_bot.send_message(LOGS_ID, text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            return await log_bot.send_message(LOGS_ID, text, parse_mode=parse_mode)
    except Exception as e:
        print(f"[LOG_BOT] Ошибка отправки сообщения: {e}")
        return None
