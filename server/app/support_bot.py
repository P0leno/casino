"""
Бот поддержки Shell
Работает в режиме polling, обрабатывает обращения пользователей
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.config import DB_PATH, BOT_TOKEN, SUPPORT_BOT_TOKEN, SUPPORT_GROUP_ID, ADMIN_IDS, SERVER_URL
import json
import os

# Антиспам: счётчики сообщений
spam_counters = defaultdict(list)  # user_id -> [timestamps]
spam_bans = {}  # user_id -> (ban_until, ban_count)

# Рейт лимит на закрытие диалога
close_rate_limit = {}  # user_id -> last_close_time

# Уведомления о блокировке (в памяти, БД - источник истины)
blocked_notified = set()  # user_id уже уведомленных о блокировке

# Инвойсы приоритета
priority_invoices = {}  # invoice_id -> {"user_id": int, "dialog_id": int}

def get_queue_size() -> int:
    """Получить размер очереди: реальные открытые обращения + надбавка"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Реальное количество открытых диалогов
    cursor.execute("SELECT COUNT(*) FROM support_dialogs WHERE status = 'open'")
    real_count = cursor.fetchone()[0]
    
    # Надбавка из БД
    cursor.execute("SELECT value FROM support_settings WHERE key = 'queue_offset'")
    offset_row = cursor.fetchone()
    offset = int(offset_row[0]) if offset_row else 0
    
    conn.close()
    
    return real_count + offset

def update_queue_offset():
    """Обновить надбавку очереди случайным числом от 10 до 20"""
    import random
    offset = random.randint(10, 20)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO support_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        ('queue_offset', str(offset))
    )
    conn.commit()
    conn.close()
    
    print(f"✅ Обновлена надбавка очереди: {offset}")

def is_user_banned(user_id: int) -> bool:
    """Проверка бана пользователя в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result[0]) if result else False

def ban_user_in_support(user_id: int, until_date: str = None):
    """Забанить пользователя ТОЛЬКО в поддержке (не трогает is_banned в аппке)
    
    Args:
        user_id: ID пользователя
        until_date: Дата разбана в формате ISO (например "2025-11-24T12:00:00") или None для постоянного бана
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем существование пользователя
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        # Создаем пользователя если его нет
        print(f"Creating user {user_id} for support ban...")
        cursor.execute(
            "INSERT INTO users (id, creation_date) VALUES (?, datetime('now'))",
            (user_id,)
        )
        conn.commit()
    
    # Обновляем support_banned и support_banned_until (НЕ is_banned!)
    cursor.execute(
        "UPDATE users SET support_banned = 1, support_banned_until = ? WHERE id = ?", 
        (until_date, user_id)
    )
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if until_date:
        print(f"Ban user {user_id} in SUPPORT until {until_date}: {rows_affected} rows affected")
    else:
        print(f"Ban user {user_id} in SUPPORT permanently: {rows_affected} rows affected")
    return True

def unban_user_in_support(user_id: int):
    """Разбанить пользователя ТОЛЬКО в поддержке (не трогает is_banned в аппке)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем существование пользователя
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        print(f"ERROR: Cannot unban user {user_id} in support - user not found in database!")
        conn.close()
        return False
    
    # Обновляем support_banned (НЕ is_banned!)
    cursor.execute("UPDATE users SET support_banned = 0 WHERE id = ?", (user_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"Unban user {user_id} in SUPPORT only: {rows_affected} rows affected")
    return True

def is_user_banned_in_support(user_id: int) -> bool:
    """Проверка бана в поддержке с учётом временного бана"""
    from datetime import datetime
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT support_banned, support_banned_until FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    support_banned, banned_until = result
    
    if not support_banned:
        return False
    
    # Если временный бан - проверяем дату
    if banned_until:
        try:
            until_dt = datetime.fromisoformat(banned_until)
            now = datetime.now()
            
            # Если срок истёк - снимаем бан
            if now >= until_dt:
                cursor = sqlite3.connect(DB_PATH).cursor()
                cursor.execute(
                    "UPDATE users SET support_banned = 0, support_banned_until = NULL WHERE id = ?", 
                    (user_id,)
                )
                cursor.connection.commit()
                cursor.connection.close()
                print(f"Support ban expired for user {user_id}")
                return False
        except:
            pass
    
    return True

def unban_user(user_id: int):
    """Разбанить пользователя в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем существование пользователя
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        print(f"ERROR: Cannot unban user {user_id} - user not found in database!")
        conn.close()
        return False
    
    # Обновляем is_banned
    cursor.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"Unban user {user_id}: {rows_affected} rows affected")
    return True

# Состояние для вывода средств
withdrawal_states = {}  # user_id -> {"amount": int, "step": "amount"|"method"}

bot = Bot(token=SUPPORT_BOT_TOKEN)
main_bot = Bot(token=BOT_TOKEN)  # Основной бот для инвойсов
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
    
    # Удаляем фото диалога
    delete_dialog_photos(dialog_id)

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

def save_message_to_dialog(dialog_id: int, sender_type: str, sender_name: str, message_text: str = None, photo_path: str = None):
    """Сохранить сообщение в историю диалога"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dialog_messages (dialog_id, sender_type, sender_name, message_text, photo_path) VALUES (?, ?, ?, ?, ?)",
        (dialog_id, sender_type, sender_name, message_text, photo_path)
    )
    conn.commit()
    conn.close()

async def download_photo(photo_file_id: str, dialog_id: int) -> str:
    """Скачать фото и сохранить в app/temp"""
    try:
        # Создаем папку если её нет
        os.makedirs("app/temp", exist_ok=True)
        
        # Получаем файл
        file = await bot.get_file(photo_file_id)
        file_path = file.file_path
        
        # Создаем имя файла
        file_extension = file_path.split('.')[-1]
        filename = f"dialog_{dialog_id}_{photo_file_id}.{file_extension}"
        local_path = f"app/temp/{filename}"
        
        # Скачиваем
        await bot.download_file(file_path, local_path)
        
        return local_path
    except Exception as e:
        print(f"Error downloading photo: {e}")
        return None

def delete_dialog_photos(dialog_id: int):
    """Удалить все фото диалога из app/temp"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT photo_path FROM dialog_messages WHERE dialog_id = ? AND photo_path IS NOT NULL",
            (dialog_id,)
        )
        photos = cursor.fetchall()
        conn.close()
        
        for (photo_path,) in photos:
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
                print(f"Deleted photo: {photo_path}")
    except Exception as e:
        print(f"Error deleting dialog photos: {e}")

async def generate_dialog_html(dialog_id: int) -> str:
    """Генерировать HTML файл диалога и вернуть путь к нему"""
    import pytz
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем информацию о диалоге
    cursor.execute(
        "SELECT user_id, username, category FROM support_dialogs WHERE dialog_id = ?",
        (dialog_id,)
    )
    dialog_info = cursor.fetchone()
    
    if not dialog_info:
        conn.close()
        return None
    
    user_id, username, category = dialog_info
    
    # Получаем сообщения диалога
    cursor.execute(
        "SELECT sender_type, sender_name, message_text, photo_path, sent_at FROM dialog_messages WHERE dialog_id = ? ORDER BY sent_at ASC",
        (dialog_id,)
    )
    messages = cursor.fetchall()
    conn.close()
    
    # Конвертируем время в МСК
    msk_tz = pytz.timezone('Europe/Moscow')
    
    def format_time_msk(time_str):
        try:
            dt = datetime.fromisoformat(time_str)
            dt_utc = pytz.utc.localize(dt)
            dt_msk = dt_utc.astimezone(msk_tz)
            return dt_msk.strftime("%d.%m.%Y %H:%M:%S")
        except:
            return time_str
    
    # Генерируем HTML с встроенными фотками (base64)
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Диалог #{dialog_id} - Поддержка Shell</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #1a1a1a; color: #fff; min-height: 100vh; padding: 20px; }}
        .user-card {{ background: #2a2a2a; border-radius: 12px; padding: 20px; margin-bottom: 20px; display: flex; align-items: center; gap: 15px; }}
        .user-avatar {{ width: 50px; height: 50px; border-radius: 50%; background: #0FBCE0; display: flex; align-items: center; justify-content: center; color: #1a1a1a; font-size: 20px; font-weight: 600; }}
        .user-details {{ flex: 1; }}
        .user-name {{ font-size: 16px; font-weight: 600; color: #0FBCE0; margin-bottom: 4px; }}
        .user-id {{ font-size: 13px; color: #888; }}
        .messages {{ max-width: 100%; }}
        .message {{ margin-bottom: 16px; }}
        .message-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .sender {{ font-weight: 500; font-size: 14px; }}
        .sender.user {{ color: #0FBCE0; }}
        .sender.support {{ color: #888; }}
        .timestamp {{ font-size: 11px; color: #666; }}
        .message-content {{ background: #2a2a2a; padding: 10px 14px; border-radius: 10px; white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.5; }}
        .message.user .message-content {{ background: rgba(15, 188, 224, 0.1); border-left: 2px solid #0FBCE0; }}
        .message.support .message-content {{ background: #2a2a2a; border-left: 2px solid #888; }}
        .message-photo {{ margin-top: 8px; border-radius: 8px; max-width: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
    </style>
</head>
<body>
    <div class="user-card">
        <div class="user-avatar">{username[0].upper() if username else "?"}</div>
        <div class="user-details">
            <div class="user-name">@{username}</div>
            <div class="user-id">ID: {user_id} • Категория: {category}</div>
        </div>
    </div>
    <div class="messages">
"""
    
    if messages:
        import base64
        for sender_type, sender_name, message_text, photo_path, sent_at in messages:
            time_formatted = format_time_msk(sent_at)
            sender_class = "user" if sender_type == "user" else "support"
            
            html += f"""
            <div class="message {sender_class}">
                <div class="message-header">
                    <span class="sender {sender_class}">{sender_name}</span>
                    <span class="timestamp">{time_formatted}</span>
                </div>
                <div class="message-content">{message_text or "(фото)"}</div>
"""
            
            if photo_path and os.path.exists(photo_path):
                try:
                    with open(photo_path, 'rb') as f:
                        photo_data = base64.b64encode(f.read()).decode()
                        ext = photo_path.split('.')[-1]
                        html += f'<img src="data:image/{ext};base64,{photo_data}" alt="Фото" class="message-photo">'
                except:
                    pass
            
            html += "</div>"
    else:
        html += '<div style="text-align: center; padding: 40px; color: #666;"><p>Нет сообщений в этом диалоге</p></div>'
    
    html += """
    </div>
</body>
</html>
"""
    
    # Сохраняем HTML в файл
    filename = f"app/temp/dialog_{dialog_id}_{user_id}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return filename

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
        [
            InlineKeyboardButton(text="❗ Проблема", callback_data="cat_problem"),
            InlineKeyboardButton(text="💡 Предложение", callback_data="cat_suggestion")
        ],
        [InlineKeyboardButton(text="📝 Другое", callback_data="cat_other")]
    ])
    return keyboard

def get_close_keyboard(dialog_id: int):
    """Клавиатура с кнопкой закрытия диалога и приоритетом"""
    # Проверяем isPriority в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT isPriority FROM support_dialogs WHERE dialog_id = ?", (dialog_id,))
    result = cursor.fetchone()
    conn.close()
    
    is_priority = result[0] if result else 0
    
    buttons = [[InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"close_{dialog_id}")]]
    
    # Показываем кнопку приоритета только если не куплена
    if not is_priority:
        buttons.append([InlineKeyboardButton(text="⭐ Приоритетная очередь", callback_data=f"priority_{dialog_id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_admin_keyboard(dialog_id: int, user_id: int, category: str, support_banned: bool = False):
    """Клавиатура для админов под сообщениями в группе"""
    
    # Для обжалования бана - три кнопки: Заблокировать в поддержке + MiniApp разбан + Не подлежит обжалованию
    if category == "Обжалование бана":
        # is_banned проверяется для аппки, показываем кнопку MiniApp разбан
        is_app_banned = is_user_banned(user_id)
        if is_app_banned:
            buttons = [
                [InlineKeyboardButton(text="🚫 Заблокировать в поддержке", callback_data=f"block_{dialog_id}_{user_id}")],
                [InlineKeyboardButton(text="✅ MiniApp разбан", callback_data=f"miniapp_unban_{dialog_id}_{user_id}")],
                [InlineKeyboardButton(text="❌ Не подлежит обжалованию", callback_data=f"reject_appeal_{dialog_id}_{user_id}")]
            ]
        else:
            # Юзер уже разбанен в аппке, остается блок в поддержке и отклонение
            buttons = [
                [InlineKeyboardButton(text="🚫 Заблокировать в поддержке", callback_data=f"block_{dialog_id}_{user_id}")],
                [InlineKeyboardButton(text="❌ Не подлежит обжалованию", callback_data=f"reject_appeal_{dialog_id}_{user_id}")]
            ]
    # Обычная кнопка бан/разбан в поддержке (только для админов)
    elif support_banned:
        ban_button = InlineKeyboardButton(text="✅ Разблокировать в поддержке", callback_data=f"unban_{dialog_id}_{user_id}")
        buttons = [[ban_button]]
    else:
        ban_button = InlineKeyboardButton(text="🚫 Заблокировать в поддержке", callback_data=f"block_{dialog_id}_{user_id}")
        buttons = [[ban_button]]
    
    # Для категории "Вывод" добавляем кнопку "Вывод выполнен"
    if category == "Вывод":
        buttons.append([InlineKeyboardButton(text="✅ Вывод выполнен", callback_data=f"withdraw_done_{dialog_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_withdrawal_confirm_keyboard():
    """Кнопка для подтверждения вывода"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Открыть обращение", callback_data="confirm_withdrawal")]
    ])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # СНАЧАЛА проверяем параметр start для обжалования бана
    # Забаненным юзерам РАЗРЕШЕНО обжаловать бан!
    args = message.text.split()
    if len(args) > 1 and args[1] == "appeal":
        withdrawal_states[user_id] = {"step": "appeal"}
        await message.answer(
            "📝 <b>Обжалование бана</b>\n\n"
            "Вы хотите обжаловать бан?\n"
            "Напишите дополнительное сообщение поддержке:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Проверка на бан В ПОДДЕРЖКЕ (только ПОСЛЕ проверки appeal!)
    # Это ПОЛНОСТЬЮ блокирует доступ к боту
    if is_user_banned_in_support(user_id):
        if user_id not in blocked_notified:
            await message.answer("⛔ Вы заблокированы в поддержке")
            blocked_notified.add(user_id)
        return
    
    # Проверка на бан в АППКЕ - НЕ блокирует доступ к поддержке!
    # Юзер может писать в поддержку по любым вопросам (вывод, тех. поддержка и т.д.)
    
    # Проверка на бан (спам)
    is_spam, ban_seconds = check_spam(user_id)
    if is_spam:
        return  # Игнорируем
    
    # Проверяем параметр start для вывода средств
    if len(args) > 1 and args[1].startswith("withdraw_"):
        try:
            amount_str = args[1].replace("withdraw_", "")
            
            # Валидация: только цифры
            if not amount_str.isdigit():
                await message.answer("❌ Некорректная сумма вывода")
                return
            
            amount = int(amount_str)
            
            # Валидация: положительное число и разумный лимит
            if amount <= 0 or amount > 1000000:
                await message.answer("❌ Некорректная сумма вывода")
                return
            
            withdrawal_states[user_id] = {"amount": amount, "step": "method"}
            
            await message.answer(
                f"💰 <b>Обналичивание реф программы</b>\n\n"
                f"Сумма: {amount} ⭐\n\n"
                f"Напишите предпочитаемый способ вывода:",
                parse_mode=ParseMode.HTML
            )
            return
        except:
            pass
    
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
        
        # Просто "Поддержка" без имени админа
        admin_prefix = "👤 <b>Поддержка:</b>\n\n"
        
        # Отправляем ответ пользователю
        try:
            print(f"📤 Отправляем ответ пользователю {user_id}")
            
            photo_path = None
            message_text = None
            
            if message.photo:
                photo = message.photo[-1]
                caption = message.caption or ""
                message_text = caption
                
                # Скачиваем фото
                photo_path = await download_photo(photo.file_id, dialog_id)
                
                print(f"📷 Отправляем фото с текстом: {caption[:50] if caption else '(пусто)'}")
                await bot.send_photo(
                    user_id,
                    photo=photo.file_id,
                    caption=f"💬 <b>Ответ поддержки</b>\n{admin_prefix}{caption}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_close_keyboard(dialog_id)
                )
            else:
                message_text = message.text
                print(f"💬 Отправляем текст: {message.text[:50] if message.text else '(пусто)'}")
                await bot.send_message(
                    user_id,
                    f"💬 <b>Ответ поддержки</b>\n{admin_prefix}{message.text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_close_keyboard(dialog_id)
                )
            
            # Сохраняем ответ в историю
            save_message_to_dialog(dialog_id, "support", "Поддержка", message_text, photo_path)
            
            # Обновляем время последнего ответа
            update_last_response(dialog_id)
            
            print(f"✅ Ответ доставлен пользователю {user_id}")
            
            # Ставим реакцию ✅ на сообщение в группе
            try:
                await bot.set_message_reaction(
                    chat_id=SUPPORT_GROUP_ID,
                    message_id=message.reply_to_message.message_id,
                    reaction=[ReactionTypeEmoji(emoji="✅")],
                    is_big=False
                )
                print(f"✅ Реакция добавлена на сообщение в группе")
            except Exception as e:
                print(f"⚠️ Не удалось поставить реакцию: {e}")
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
        "cat_suggestion": "Предложение",
        "cat_other": "Другое"
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
    
    # СНАЧАЛА обработка обжалования бана и вывода средств
    # Забаненным юзерам РАЗРЕШЕНО обжаловать бан!
    if user_id in withdrawal_states:
        state = withdrawal_states[user_id]
        
        # Обработка обжалования бана
        if state["step"] == "appeal":
            appeal_text = message.text or "(фото)"
            username = message.from_user.username or "без username"
            
            await message.answer(
                f"📋 <b>Ваше обращение:</b>\n\n"
                f"Тема: Обжалование бана\n"
                f"Сообщение: {appeal_text}\n\n"
                f"Нажмите кнопку ниже для отправки:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_withdrawal_confirm_keyboard()
            )
            
            withdrawal_states[user_id]["message"] = appeal_text
            withdrawal_states[user_id]["step"] = "appeal_confirm"
            return
        
        if state["step"] == "method":
            method = message.text or "(фото)"
            amount = state["amount"]
            
            await message.answer(
                f"📋 <b>Ваше обращение:</b>\n\n"
                f"Тема: Обналичивание реф программы\n"
                f"Сумма: {amount} ⭐\n"
                f"Способ: {method}\n\n"
                f"Нажмите кнопку ниже для отправки:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_withdrawal_confirm_keyboard()
            )
            
            # Сохраняем способ
            withdrawal_states[user_id]["method"] = method
            withdrawal_states[user_id]["step"] = "confirm"
            return
    
    # Проверка на бан В ПОДДЕРЖКЕ (только ПОСЛЕ обработки withdrawal_states!)
    # Это ПОЛНОСТЬЮ блокирует доступ к боту
    if is_user_banned_in_support(user_id):
        if user_id not in blocked_notified:
            await message.answer("⛔ Вы заблокированы в поддержке")
            blocked_notified.add(user_id)
        return
    
    # Проверка на бан в АППКЕ - НЕ блокирует доступ к поддержке!
    # Юзер может писать в поддержку по любым вопросам (вывод, тех. поддержка и т.д.)
    
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
        # Проверяем текущий статус бана для правильной кнопки
        user_support_banned = is_user_banned_in_support(user_id)
        
        # Сохраняем сообщение в БД
        photo_path = None
        if message.photo:
            # Скачиваем фото
            photo = message.photo[-1]
            photo_path = await download_photo(photo.file_id, dialog_id)
            
            # Отправляем в группу
            caption = header + (text if text else "(без текста)")
            await bot.send_photo(
                SUPPORT_GROUP_ID,
                photo=photo.file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard(dialog_id, user_id, category, user_support_banned)
            )
        else:
            # Только текст
            await bot.send_message(
                SUPPORT_GROUP_ID,
                header + text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard(dialog_id, user_id, category, user_support_banned)
            )
        
        # Сохраняем в историю
        save_message_to_dialog(dialog_id, "user", username, text if text else None, photo_path)
        
        queue_size = get_queue_size()
        
        await message.answer(
            f"✅ <b>Сообщение успешно доставлено в команду поддержки</b>\n\n"
            f"Очередь: {queue_size}\n"
            f"Ожидайте ответа",
            parse_mode=ParseMode.HTML,
            reply_markup=get_close_keyboard(dialog_id)
        )
    except Exception as e:
        print(f"Error sending to support group: {e}")
        await message.answer("❌ Ошибка отправки сообщения")

@dp.callback_query(F.data == "confirm_withdrawal")
async def handle_confirm_withdrawal(callback: CallbackQuery):
    """Подтверждение вывода средств или обжалования бана"""
    user_id = callback.from_user.id
    
    if user_id not in withdrawal_states:
        await callback.answer("Ошибка: состояние не найдено", show_alert=True)
        return
    
    state = withdrawal_states[user_id]
    username = callback.from_user.username or "без username"
    
    # Обработка обжалования бана
    if state["step"] == "appeal_confirm":
        appeal_message = state["message"]
        
        # Создаем диалог с категорией "Обжалование бана"
        dialog_id = create_dialog(user_id, username, "Обжалование бана")
        
        # Сохраняем первое сообщение в историю
        save_message_to_dialog(dialog_id, "user", username, appeal_message, None)
        
        # Отправляем в группу
        header = (
            f"📨 <b>Диалог #{dialog_id}</b>\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📁 Категория: ⚠️ <b>ОБЖАЛОВАНИЕ БАНА</b>\n\n"
            f"📝 Сообщение: {appeal_message}"
        )
        
        try:
            # При обжаловании бана пользователь ВСЕГДА забанен
            # (иначе он не мог бы открыть обжалование)
            
            await bot.send_message(
                SUPPORT_GROUP_ID,
                header,
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard(dialog_id, user_id, "Обжалование бана")
            )
            
            queue_size = get_queue_size()
            
            await callback.message.edit_text(
                f"✅ <b>Обращение создано!</b>\n\n"
                f"Очередь: {queue_size}\n"
                f"Ожидайте ответа поддержки",
                parse_mode=ParseMode.HTML,
                reply_markup=get_close_keyboard(dialog_id)
            )
            
            del withdrawal_states[user_id]
            
        except Exception as e:
            print(f"Error creating appeal dialog: {e}")
            await callback.answer("Ошибка создания обращения", show_alert=True)
        
        await callback.answer()
        return
    
    # Обработка вывода средств
    if state["step"] != "confirm":
        await callback.answer("Ошибка: состояние вывода не найдено", show_alert=True)
        return
    
    amount = state["amount"]
    method = state["method"]
    
    # Создаем диалог с категорией "Вывод"
    dialog_id = create_dialog(user_id, username, "Вывод")
    
    # Сохраняем первое сообщение в историю
    withdrawal_text = f"💰 Обналичивание реф программы\nСумма: {amount} ⭐\nСпособ: {method}"
    save_message_to_dialog(dialog_id, "user", username, withdrawal_text, None)
    
    # Отправляем в группу
    header = (
        f"📨 <b>Диалог #{dialog_id}</b>\n"
        f"👤 @{username} (ID: {user_id})\n"
        f"📁 Категория: Вывод\n\n"
        f"💰 <b>Обналичивание реф программы</b>\n"
        f"Сумма: {amount} ⭐\n"
        f"Способ: {method}"
    )
    
    try:
        user_support_banned = is_user_banned_in_support(user_id)
        
        await bot.send_message(
            SUPPORT_GROUP_ID,
            header,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard(dialog_id, user_id, "Вывод", user_support_banned)
        )
        
        queue_size = get_queue_size()
        
        await callback.message.edit_text(
            f"✅ <b>Обращение создано!</b>\n\n"
            f"Очередь: {queue_size}\n"
            f"Ожидайте ответа поддержки",
            parse_mode=ParseMode.HTML,
            reply_markup=get_close_keyboard(dialog_id)
        )
        
        # Очищаем состояние
        del withdrawal_states[user_id]
        
    except Exception as e:
        print(f"Error creating withdrawal dialog: {e}")
        await callback.answer("Ошибка создания обращения", show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data.startswith("block_"))
async def handle_block_user(callback: CallbackQuery):
    """Блокировка пользователя ТОЛЬКО в поддержке (не трогает аппку)"""
    admin_id = callback.from_user.id
    
    # Проверка прав админа
    if admin_id not in ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    try:
        parts = callback.data.split("_")
        dialog_id = int(parts[1])
        user_id = int(parts[2])
        
        # Баним ТОЛЬКО в поддержке (НЕ трогаем is_banned!)
        success = ban_user_in_support(user_id)
        if not success:
            await callback.answer("❌ Пользователь не найден в БД", show_alert=True)
            return
        
        blocked_notified.add(user_id)  # Помечаем что уведомили
        
        # Уведомляем пользователя
        try:
            await bot.send_message(user_id, "⛔ Вы заблокированы в поддержке")
        except:
            pass
        
        # Закрываем диалог
        close_dialog(dialog_id)
        
        # Получаем категорию диалога
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category FROM support_dialogs WHERE dialog_id = ?", (dialog_id,))
        result = cursor.fetchone()
        conn.close()
        
        category = result[0] if result else ""
        
        # Меняем кнопку на "Разблокировать в поддержке"
        # Для закрытого диалога обжалования НЕ показываем MiniApp разбан, только обычную разблокировку
        if category == "Обжалование бана":
            category = ""  # Убираем категорию, чтобы показалась обычная кнопка разблокировки
        
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_keyboard(dialog_id, user_id, category, support_banned=True)
        )
        await callback.answer("✅ Пользователь заблокирован")
        
    except Exception as e:
        print(f"Error blocking user: {e}")
        await callback.answer("Ошибка блокировки", show_alert=True)

@dp.callback_query(F.data.startswith("miniapp_unban_"))
async def handle_miniapp_unban_user(callback: CallbackQuery):
    """Разблокировка через miniApp - доступна всем при обжаловании"""
    # НЕ проверяем ADMIN_IDS - доступна всем
    
    try:
        parts = callback.data.split("_")
        dialog_id = int(parts[2])
        user_id = int(parts[3])
        
        # Разбаниваем в БД
        success = unban_user(user_id)
        if not success:
            await callback.answer("❌ Пользователь не найден в БД", show_alert=True)
            return
        
        blocked_notified.discard(user_id)
        
        # Уведомляем пользователя с кнопкой-ссылкой на приложение
        try:
            app_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Открыть Shell", url="https://t.me/shellgiftbot/shell")]
            ])
            await bot.send_message(
                user_id,
                "✅ <b>Вы были разблокированы в MiniApp</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=app_button
            )
        except:
            pass
        
        # Получаем категорию диалога
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category FROM support_dialogs WHERE dialog_id = ?", (dialog_id,))
        result = cursor.fetchone()
        conn.close()
        
        category = result[0] if result else ""
        
        # Закрываем диалог обжалования
        close_dialog(dialog_id)
        
        # Убираем кнопки (диалог закрыт)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Пользователь разблокирован в MiniApp, диалог закрыт")
        
    except Exception as e:
        print(f"Error with miniapp unban: {e}")
        await callback.answer("Ошибка разблокировки", show_alert=True)

@dp.callback_query(F.data.startswith("reject_appeal_"))
async def handle_reject_appeal(callback: CallbackQuery):
    """Отклонение обжалования - бан в поддержке на 1 день"""
    admin_id = callback.from_user.id
    
    # Проверка прав админа
    if admin_id not in ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    try:
        parts = callback.data.split("_")
        dialog_id = int(parts[2])
        user_id = int(parts[3])
        
        # Выдаём бан в поддержке на 1 день
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        until_date = tomorrow.isoformat()
        
        success = ban_user_in_support(user_id, until_date)
        if not success:
            await callback.answer("❌ Пользователь не найден в БД", show_alert=True)
            return
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user_id,
                "❌ <b>Бан обжалованию не подлежит</b>\n\n"
                "Бан в поддержке выдан на 1 день за ложное обращение.\n"
                f"Разбан: {tomorrow.strftime('%d.%m.%Y %H:%M')}",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        # Закрываем диалог
        close_dialog(dialog_id)
        
        # Добавляем сообщение в группу
        await bot.send_message(
            SUPPORT_GROUP_ID,
            f"❌ <b>Обжалование отклонено</b>\n\n"
            f"Пользователь забанен в поддержке на 1 день за ложное обращение.\n"
            f"Разбан: {tomorrow.strftime('%d.%m.%Y %H:%M')}",
            parse_mode=ParseMode.HTML
        )
        
        # Убираем кнопки
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Обжалование отклонено, выдан бан в поддержке на 1 день")
        
    except Exception as e:
        print(f"Error rejecting appeal: {e}")
        await callback.answer("Ошибка отклонения обжалования", show_alert=True)

@dp.callback_query(F.data.startswith("unban_"))
async def handle_unban_user(callback: CallbackQuery):
    """Разблокировка пользователя ТОЛЬКО в поддержке (не трогает аппку)"""
    admin_id = callback.from_user.id
    
    # Проверка прав админа - ТОЛЬКО админы
    if admin_id not in ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    try:
        parts = callback.data.split("_")
        dialog_id = int(parts[1])
        user_id = int(parts[2])
        
        # Разбаниваем ТОЛЬКО в поддержке (НЕ трогаем is_banned!)
        success = unban_user_in_support(user_id)
        if not success:
            await callback.answer("❌ Пользователь не найден в БД", show_alert=True)
            return
        
        blocked_notified.discard(user_id)  # Убираем из уведомленных
        
        # Уведомляем пользователя
        try:
            await bot.send_message(user_id, "✅ Вы разблокированы в поддержке")
        except:
            pass
        
        # Получаем категорию диалога
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category FROM support_dialogs WHERE dialog_id = ?", (dialog_id,))
        result = cursor.fetchone()
        conn.close()
        
        category = result[0] if result else ""
        
        # Меняем кнопку на "Заблокировать в поддержке"
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_keyboard(dialog_id, user_id, category, support_banned=False)
        )
        await callback.answer("✅ Пользователь разблокирован")
        
    except Exception as e:
        print(f"Error unblocking user: {e}")
        await callback.answer("Ошибка разблокировки", show_alert=True)

@dp.callback_query(F.data.startswith("withdraw_done_"))
async def handle_withdraw_done(callback: CallbackQuery):
    """Отметка о выполнении вывода"""
    admin_id = callback.from_user.id
    
    # Проверка прав админа
    if admin_id not in ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    try:
        dialog_id = int(callback.data.replace("withdraw_done_", ""))
        
        # Получаем user_id из диалога
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM support_dialogs WHERE dialog_id = ?", (dialog_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id = result[0]
            
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    user_id,
                    "✅ <b>Вывод выполнен!</b>\n\nСпасибо за использование Shell",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            # Закрываем диалог
            close_dialog(dialog_id)
            
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("✅ Вывод отмечен как выполненный")
        else:
            await callback.answer("Диалог не найден", show_alert=True)
            
    except Exception as e:
        print(f"Error marking withdrawal done: {e}")
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("priority_"))
async def handle_priority_queue(callback: CallbackQuery):
    """Обработка запроса на приоритетную очередь"""
    user_id = callback.from_user.id
    
    # Проверка на бан - игнорируем полностью
    if user_id in spam_bans:
        ban_until, _ = spam_bans[user_id]
        if datetime.now() < ban_until:
            return  # Игнорируем без ответа
    
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
        
        # Создаем инвойс на 1 звезду через основной бот
        title = "Приоритетная очередь"
        description = "Ваше обращение будет выделено и уведомит всех сотрудников поддержки"
        payload = json.dumps({"type": "priority", "dialog_id": dialog_id, "user_id": user_id})
        currency = "XTR"  # Telegram Stars
        prices = [LabeledPrice(label="1 звезда", amount=1)]
        
        try:
            invoice_link = await main_bot.create_invoice_link(
                title=title,
                description=description,
                payload=payload,
                currency=currency,
                prices=prices
            )
            
            # Сохраняем информацию о инвойсе
            # priority_invoices[invoice_id] = {"user_id": user_id, "dialog_id": dialog_id}
            # Но мы используем payload для этого
            
            # Отправляем пользователю инвойс
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить 1⭐", url=invoice_link)],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_priority_{dialog_id}")]
            ])
            
            await callback.message.answer(
                "⭐ <b>Приоритетная очередь</b>\n\n"
                "Стоимость: 1 звезда\n\n"
                "После оплаты:\n"
                "• Ваше обращение будет выделено\n"
                "• Все сотрудники поддержки получат уведомление\n"
                "• Приоритетная обработка",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            await callback.answer()
            
        except Exception as e:
            print(f"Error creating priority invoice: {e}")
            await callback.answer("Ошибка создания платежа", show_alert=True)
            
    except Exception as e:
        print(f"Error handling priority queue: {e}")
        await callback.answer("Ошибка обработки запроса", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_priority_"))
async def handle_cancel_priority(callback: CallbackQuery):
    """Отмена приоритетной очереди"""
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        print(f"Error canceling priority: {e}")
        # Игнорируем ошибки старых callback

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
        
        try:
            await callback.message.edit_text(
                "✅ <b>Обращение закрыто</b>\n\n"
                "Спасибо за обращение!\n"
                "Используйте /start для нового обращения",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            # Если не удалось редактировать, отправляем новое сообщение
            print(f"Could not edit message, sending new: {e}")
            await bot.send_message(
                user_id,
                "✅ <b>Обращение закрыто</b>\n\n"
                "Спасибо за обращение!\n"
                "Используйте /start для нового обращения",
                parse_mode=ParseMode.HTML
            )
        
        # Генерируем и отправляем HTML файл в группу
        try:
            from aiogram.types import FSInputFile
            
            # Генерируем HTML
            html_path = await generate_dialog_html(dialog_id)
            
            if html_path and os.path.exists(html_path):
                # Отправляем HTML файл
                html_file = FSInputFile(html_path)
                await bot.send_document(
                    SUPPORT_GROUP_ID,
                    html_file,
                    caption=f"✅ <b>Диалог #{dialog_id} закрыт пользователем</b>",
                    parse_mode=ParseMode.HTML
                )
                
                # Удаляем HTML файл
                os.remove(html_path)
                print(f"Deleted HTML: {html_path}")
            else:
                # Если HTML не создан, просто отправляем текст
                await bot.send_message(
                    SUPPORT_GROUP_ID,
                    f"✅ <b>Диалог #{dialog_id} закрыт пользователем</b>",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"Error sending dialog HTML: {e}")
            # Пробуем хотя бы отправить текст
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

async def update_queue_offset_task():
    """Фоновая задача для обновления надбавки очереди каждые 3 часа"""
    while True:
        await asyncio.sleep(10800)  # 3 часа = 10800 секунд
        update_queue_offset()

async def get_group_members() -> list:
    """Получить список участников группы поддержки"""
    try:
        members = []
        chat = await bot.get_chat(SUPPORT_GROUP_ID)
        
        # Получаем список админов
        admins = await bot.get_chat_administrators(SUPPORT_GROUP_ID)
        
        for admin in admins:
            # Пропускаем бота
            if admin.user.id == (await bot.get_me()).id:
                continue
            
            username = f"@{admin.user.username}" if admin.user.username else admin.user.full_name
            members.append({"id": admin.user.id, "mention": username})
        
        return members
    except Exception as e:
        print(f"Error getting group members: {e}")
        return []

async def start_support_bot():
    """Запуск бота поддержки"""
    if not SUPPORT_BOT_TOKEN:
        print("⚠️  SUPPORT_BOT_TOKEN не настроен - бот поддержки отключен")
        return
    
    if not SUPPORT_GROUP_ID:
        print("⚠️  SUPPORT_GROUP_ID не настроен - бот поддержки отключен")
        return
    
    print("✅ Бот поддержки запущен (polling mode)")
    
    try:
        # Запускаем фоновые задачи
        asyncio.create_task(notify_ban_expired())
        asyncio.create_task(update_queue_offset_task())
        
        # Запускаем polling (он блокирует, поэтому должен быть в отдельной задаче)
        # Указываем allowed_updates для получения всех типов сообщений
        await dp.start_polling(
            bot, 
            skip_updates=True,
            allowed_updates=["message", "callback_query", "pre_checkout_query", "message_reaction"]
        )
    except Exception as e:
        print(f"❌ Ошибка бота поддержки: {e}")
    finally:
        print("🛑 Бот поддержки остановлен")
