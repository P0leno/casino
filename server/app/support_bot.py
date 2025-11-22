"""
Бот поддержки Shell
Работает в режиме polling, обрабатывает обращения пользователей
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.config import DB_PATH, SUPPORT_BOT_TOKEN, SUPPORT_GROUP_ID

# Антиспам: счётчики сообщений
spam_counters = defaultdict(list)  # user_id -> [timestamps]
spam_bans = {}  # user_id -> (ban_until, ban_count)

# Рейт лимит на закрытие диалога
close_rate_limit = {}  # user_id -> last_close_time

bot = Bot(token=SUPPORT_BOT_TOKEN)
dp = Dispatcher()

def get_active_dialog(user_id: int):
    """Получить активный диалог пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT dialog_id, category, last_response_at FROM support_dialogs WHERE user_id = ? AND status = 'open'",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def create_dialog(user_id: int, username: str, category: str):
    """Создать новый диалог"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO support_dialogs (user_id, username, category) VALUES (?, ?, ?)",
        (user_id, username, category)
    )
    dialog_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return dialog_id

def close_dialog(dialog_id: int):
    """Закрыть диалог"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE support_dialogs SET status = 'closed', closed_at = ? WHERE dialog_id = ?",
        (datetime.now(), dialog_id)
    )
    conn.commit()
    conn.close()

def update_last_response(dialog_id: int):
    """Обновить время последнего ответа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE support_dialogs SET last_response_at = ? WHERE dialog_id = ?",
        (datetime.now(), dialog_id)
    )
    conn.commit()
    conn.close()

def check_spam(user_id: int) -> tuple[bool, int]:
    """
    Проверка на спам
    Возвращает (is_spam, ban_seconds)
    """
    now = datetime.now()
    
    # Проверяем активный бан
    if user_id in spam_bans:
        ban_until, ban_count = spam_bans[user_id]
        if now < ban_until:
            remaining = int((ban_until - now).total_seconds())
            return True, remaining
        else:
            # Бан истёк
            del spam_bans[user_id]
    
    # Очищаем старые сообщения (старше 6 секунд)
    cutoff = now - timedelta(seconds=6)
    spam_counters[user_id] = [ts for ts in spam_counters[user_id] if ts > cutoff]
    
    # Добавляем текущее сообщение
    spam_counters[user_id].append(now)
    
    # Проверяем: 3+ сообщения за 6 секунд = спам
    if len(spam_counters[user_id]) >= 3:
        # Определяем длительность бана
        ban_count = spam_bans.get(user_id, (None, 0))[1] + 1
        ban_duration = 60 * (2 ** (ban_count - 1))  # 60, 120, 240, ...
        ban_until = now + timedelta(seconds=ban_duration)
        spam_bans[user_id] = (ban_until, ban_count)
        
        return True, ban_duration
    
    return False, 0

def get_main_keyboard():
    """Главное меню с категориями"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗ Проблема", callback_data="cat_problem")],
        [InlineKeyboardButton(text="💰 Вывод", callback_data="cat_withdraw")],
        [InlineKeyboardButton(text="👥 Рефка", callback_data="cat_referral")],
        [InlineKeyboardButton(text="💡 Предложение", callback_data="cat_suggestion")]
    ])
    return keyboard

def get_close_keyboard(dialog_id: int):
    """Клавиатура с кнопкой закрытия диалога"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"close_{dialog_id}")]
    ])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Проверка на бан
    is_spam, ban_seconds = check_spam(user_id)
    if is_spam:
        return  # Игнорируем
    
    # Проверяем последний ответ
    dialog = get_active_dialog(user_id)
    last_response_text = "Нет активных обращений"
    
    if dialog:
        dialog_id, category, last_response_at = dialog
        if last_response_at:
            last_response_text = f"Последний ответ: {last_response_at}"
        else:
            last_response_text = "Ожидает ответа поддержки"
    
    await message.answer(
        f"👋 <b>Здравствуйте, это бот поддержки Shell</b>\n\n"
        f"📝 {last_response_text}\n\n"
        f"Выберите категорию обращения:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

@dp.message(F.reply_to_message)
async def handle_admin_reply(message: Message):
    """Обработка ответа админа в группе"""
    print(f"📩 Получен reply в чате {message.chat.id} (нужен {SUPPORT_GROUP_ID})")
    
    # Проверяем что это группа поддержки
    if message.chat.id != SUPPORT_GROUP_ID:
        print(f"⚠️  Не та группа, игнорируем")
        return
    
    print(f"✅ Это группа поддержки, обрабатываем reply")
    
    try:
        # Извлекаем dialog_id из оригинального сообщения
        original_text = message.reply_to_message.text or message.reply_to_message.caption
        print(f"📝 Оригинальный текст: {original_text[:100] if original_text else 'None'}")
        
        if not original_text or "Диалог #" not in original_text:
            print(f"⚠️  Нет 'Диалог #' в тексте, игнорируем")
            return
        
        # Парсим dialog_id
        dialog_id_str = original_text.split("Диалог #")[1].split("\n")[0]
        dialog_id = int(dialog_id_str)
        print(f"🔍 Найден dialog_id: {dialog_id}")
        
        # Получаем информацию о диалоге
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, status FROM support_dialogs WHERE dialog_id = ?",
            (dialog_id,)
        )
        dialog_info = cursor.fetchone()
        conn.close()
        
        if not dialog_info:
            print(f"❌ Диалог #{dialog_id} не найден в БД")
            await message.reply("❌ Диалог не найден")
            return
        
        user_id, status = dialog_info
        print(f"📋 Диалог #{dialog_id}: user_id={user_id}, status={status}")
        
        if status != 'open':
            print(f"❌ Диалог #{dialog_id} уже закрыт")
            await message.reply("❌ Диалог уже закрыт")
            return
        
        # Формируем имя админа
        admin_name = message.from_user.username or message.from_user.first_name or "Админ"
        admin_prefix = f"👤 <b>{admin_name}:</b>\n\n"
        
        # Отправляем ответ пользователю
        try:
            print(f"📤 Отправляем ответ пользователю {user_id}")
            
            if message.photo:
                photo = message.photo[-1]
                caption = message.caption or ""
                print(f"📷 Отправляем фото с текстом: {caption[:50] if caption else '(пусто)'}")
                await bot.send_photo(
                    user_id,
                    photo=photo.file_id,
                    caption=f"💬 <b>Ответ поддержки</b>\n{admin_prefix}{caption}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_close_keyboard(dialog_id)
                )
            else:
                print(f"💬 Отправляем текст: {message.text[:50] if message.text else '(пусто)'}")
                await bot.send_message(
                    user_id,
                    f"💬 <b>Ответ поддержки</b>\n{admin_prefix}{message.text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_close_keyboard(dialog_id)
                )
            
            # Обновляем время последнего ответа
            update_last_response(dialog_id)
            
            print(f"✅ Ответ доставлен пользователю {user_id}")
            await message.reply("✅ Сообщение доставлено пользователю")
        except Exception as e:
            print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
            await message.reply(f"❌ Не удалось доставить сообщение: {e}")
    
    except Exception as e:
        print(f"Error handling admin reply: {e}")

@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверка на бан - игнорируем полностью
    if user_id in spam_bans:
        ban_until, _ = spam_bans[user_id]
        if datetime.now() < ban_until:
            return  # Игнорируем без ответа
    
    # Проверяем активный диалог
    active_dialog = get_active_dialog(user_id)
    if active_dialog:
        await callback.answer("У вас уже есть активное обращение", show_alert=True)
        return
    
    category_map = {
        "cat_problem": "Проблема",
        "cat_withdraw": "Вывод",
        "cat_referral": "Рефка",
        "cat_suggestion": "Предложение"
    }
    
    category = category_map.get(callback.data)
    username = callback.from_user.username or "без username"
    
    # Создаём диалог
    dialog_id = create_dialog(user_id, username, category)
    
    await callback.message.edit_text(
        f"📩 <b>Категория: {category}</b>\n\n"
        f"Напишите сообщение для поддержки (только текст и фото)",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.message(F.text | F.photo)
async def handle_user_message(message: Message):
    user_id = message.from_user.id
    
    # Игнорируем все сообщения из группы (только личные сообщения)
    if message.chat.type != "private":
        return
    
    # Проверка на бан (сохраняем предыдущий статус)
    was_banned = user_id in spam_bans and datetime.now() < spam_bans[user_id][0]
    is_spam, ban_seconds = check_spam(user_id)
    
    if is_spam:
        # Показываем сообщение о бане только первый раз (когда только что забанили)
        if not was_banned and ban_seconds > 0:
            minutes = ban_seconds // 60
            await message.answer(
                f"⛔ <b>Вы спамили!</b>\n\n"
                f"Наказание: молчание на {minutes} минут",
                parse_mode=ParseMode.HTML
            )
        # Все остальные сообщения игнорируем молча
        return
    
    # Проверяем активный диалог
    dialog = get_active_dialog(user_id)
    if not dialog:
        await message.answer(
            "❌ У вас нет активного обращения\n\n"
            "Используйте /start для создания нового обращения"
        )
        return
    
    dialog_id, category, last_response_at = dialog
    username = message.from_user.username or "без username"
    
    # Формируем сообщение для группы
    text = message.text or message.caption or ""
    header = (
        f"📨 <b>Диалог #{dialog_id}</b>\n"
        f"👤 @{username} (ID: {user_id})\n"
        f"📁 Категория: {category}\n\n"
    )
    
    try:
        if message.photo:
            # Фото с подписью
            photo = message.photo[-1]
            caption = header + (text if text else "(без текста)")
            await bot.send_photo(
                SUPPORT_GROUP_ID,
                photo=photo.file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        else:
            # Только текст
            await bot.send_message(
                SUPPORT_GROUP_ID,
                header + text,
                parse_mode=ParseMode.HTML
            )
        
        await message.answer(
            "✅ <b>Сообщение успешно доставлено в команду поддержки</b>\n\n"
            "Ожидайте ответа",
            parse_mode=ParseMode.HTML,
            reply_markup=get_close_keyboard(dialog_id)
        )
    except Exception as e:
        print(f"Error sending to support group: {e}")
        await message.answer("❌ Ошибка отправки сообщения")

@dp.callback_query(F.data.startswith("close_"))
async def handle_close_dialog(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверка на бан - игнорируем полностью
    if user_id in spam_bans:
        ban_until, _ = spam_bans[user_id]
        if datetime.now() < ban_until:
            return  # Игнорируем без ответа
    
    # Рейт лимит на закрытие: 1 раз в минуту
    now = datetime.now()
    if user_id in close_rate_limit:
        last_close = close_rate_limit[user_id]
        if now - last_close < timedelta(minutes=1):
            remaining = 60 - int((now - last_close).total_seconds())
            await callback.answer(f"Попробуйте через {remaining}с", show_alert=True)
            return
    
    try:
        dialog_id = int(callback.data.split("_")[1])
        
        # Проверяем что диалог принадлежит пользователю
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, status FROM support_dialogs WHERE dialog_id = ?",
            (dialog_id,)
        )
        dialog_info = cursor.fetchone()
        conn.close()
        
        if not dialog_info:
            await callback.answer("Диалог не найден", show_alert=True)
            return
        
        dialog_user_id, status = dialog_info
        
        if dialog_user_id != user_id:
            await callback.answer("Это не ваш диалог", show_alert=True)
            return
        
        if status != 'open':
            await callback.answer("Диалог уже закрыт", show_alert=True)
            return
        
        # Закрываем диалог
        close_dialog(dialog_id)
        close_rate_limit[user_id] = now
        
        await callback.message.edit_text(
            "✅ <b>Обращение закрыто</b>\n\n"
            "Спасибо за обращение!\n"
            "Используйте /start для нового обращения",
            parse_mode=ParseMode.HTML
        )
        
        # Уведомляем группу
        try:
            await bot.send_message(
                SUPPORT_GROUP_ID,
                f"✅ <b>Диалог #{dialog_id} закрыт пользователем</b>",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        await callback.answer("Обращение закрыто")
    
    except Exception as e:
        print(f"Error closing dialog: {e}")
        await callback.answer("Ошибка закрытия обращения", show_alert=True)

async def notify_ban_expired():
    """Фоновая задача для уведомления о снятии бана"""
    while True:
        await asyncio.sleep(10)  # Проверяем каждые 10 секунд
        
        now = datetime.now()
        expired_bans = []
        
        for user_id, (ban_until, ban_count) in list(spam_bans.items()):
            if now >= ban_until:
                expired_bans.append(user_id)
                
                # Получаем активный диалог
                dialog = get_active_dialog(user_id)
                if dialog:
                    dialog_id = dialog[0]
                    try:
                        await bot.send_message(
                            user_id,
                            f"✅ <b>Вы снова можете писать</b>\n\n"
                            f"Открытый диалог: #{dialog_id}",
                            parse_mode=ParseMode.HTML,
                            reply_markup=get_close_keyboard(dialog_id)
                        )
                    except:
                        pass
        
        # Удаляем истёкшие баны
        for user_id in expired_bans:
            del spam_bans[user_id]

async def start_support_bot():
    """Запуск бота поддержки"""
    if not SUPPORT_BOT_TOKEN:
        print("⚠️  SUPPORT_BOT_TOKEN не настроен - бот поддержки отключен")
        return
    
    if not SUPPORT_GROUP_ID:
        print("⚠️  SUPPORT_GROUP_ID не настроен - бот поддержки отключен")
        return
    
    try:
        print("✅ Бот поддержки запущен (polling mode)")
        
        # Запускаем фоновую задачу для уведомлений
        asyncio.create_task(notify_ban_expired())
        
        # Запускаем polling (он блокирует, поэтому должен быть в отдельной задаче)
        # Указываем allowed_updates для получения всех типов сообщений
        await dp.start_polling(
            bot, 
            skip_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        print(f"❌ Ошибка бота поддержки: {e}")
    finally:
        print("🛑 Бот поддержки остановлен")
