"""
Антифрод система для Shell
- Проверяет БД каждые 5 минут на дубликаты IP
- Автоматически банит при мошенничестве с промокодами
"""
import asyncio
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
import json
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import DB_PATH

async def send_antifraud_alert(alert_type: str, users: list, ip: str):
    """Отправляет алерт в канал логов"""
    from app.log_bot import send_message_to_logs
    
    if alert_type == "warning":
        # Предупреждение - одинаковый IP
        text = "⚠️ <b>АНТИФРОД ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
        text += f"🌐 IP: <code>{ip}</code>\n\n"
        text += "👥 <b>Пользователи:</b>\n"
        
        user_ids = []
        for user in users:
            user_ids.append(str(user['id']))
            text += f"• ID: <code>{user['id']}</code> | @{user['username'] or 'нет'}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Заблокировать всех", callback_data=f"af_ban_{ip}_{','.join(user_ids)}"),
                InlineKeyboardButton(text="✅ Игнорировать", callback_data=f"af_ignore_{ip}_{','.join(user_ids)}")
            ]
        ])
        
        await send_message_to_logs(text, reply_markup=keyboard)
        
    elif alert_type == "ban":
        # Автоматический бан - мошенничество с промокодами
        text = "🚨 <b>АНТИФРОД БАН</b>\n\n"
        text += f"🌐 IP: <code>{ip}</code>\n"
        text += "📛 <b>Причина:</b> Мошенничество с промокодами\n\n"
        text += "👥 <b>Заблокированы:</b>\n"
        
        user_ids = []
        for user in users:
            user_ids.append(str(user['id']))
            text += f"• ID: <code>{user['id']}</code> | @{user['username'] or 'нет'}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разбанить всех", callback_data=f"af_unban_{','.join(user_ids)}")]
        ])
        
        await send_message_to_logs(text, reply_markup=keyboard)


def get_users_by_ip() -> dict:
    """Получает словарь IP -> список пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, ip_addresses FROM users WHERE ip_addresses IS NOT NULL AND ip_addresses != '[]'")
    rows = cursor.fetchall()
    conn.close()
    
    ip_users = {}  # ip -> [user_ids]
    
    for user_id, username, ip_json in rows:
        try:
            ip_list = json.loads(ip_json) if ip_json else []
            for ip in ip_list:
                if ip and ip != "unknown":
                    if ip not in ip_users:
                        ip_users[ip] = []
                    ip_users[ip].append({
                        'id': user_id,
                        'username': username
                    })
        except:
            continue
    
    return ip_users


def is_ip_ignored(ip: str, user_ids: list) -> bool:
    """Проверяет, игнорируется ли эта комбинация IP + юзеров"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_ids FROM antifraud_ignored WHERE ip_address = ?", (ip,))
    rows = cursor.fetchall()
    conn.close()
    
    user_ids_set = set(user_ids)
    
    for (stored_ids,) in rows:
        try:
            stored_set = set(json.loads(stored_ids))
            # Если все текущие юзеры уже в игнорируемом списке
            if user_ids_set.issubset(stored_set):
                return True
        except:
            continue
    
    return False


def is_alert_sent(alert_type: str, ip: str, user_ids: list) -> bool:
    """Проверяет, был ли уже отправлен такой алерт"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_ids_json = json.dumps(sorted(user_ids))
    
    cursor.execute(
        "SELECT id FROM antifraud_alerts WHERE alert_type = ? AND ip_address = ? AND user_ids = ?",
        (alert_type, ip, user_ids_json)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def mark_alert_sent(alert_type: str, ip: str, user_ids: list):
    """Помечает алерт как отправленный"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_ids_json = json.dumps(sorted(user_ids))
    
    cursor.execute(
        "INSERT INTO antifraud_alerts (alert_type, ip_address, user_ids, created_at) VALUES (?, ?, ?, ?)",
        (alert_type, ip, user_ids_json, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def ban_users(user_ids: list):
    """Банит пользователей в миниаппке"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for user_id in user_ids:
        cursor.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    print(f"[ANTIFRAUD] Забанены пользователи: {user_ids}")


def unban_users(user_ids: list):
    """Разбанивает пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for user_id in user_ids:
        cursor.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    print(f"[ANTIFRAUD] Разбанены пользователи: {user_ids}")


def ignore_ip_users(ip: str, user_ids: list):
    """Добавляет комбинацию IP + юзеров в игнорируемые"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_ids_json = json.dumps(user_ids)
    
    cursor.execute(
        "INSERT INTO antifraud_ignored (ip_address, user_ids, ignored_at) VALUES (?, ?, ?)",
        (ip, user_ids_json, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"[ANTIFRAUD] IP {ip} с юзерами {user_ids} добавлен в игнорируемые")


async def check_duplicate_ips():
    """Проверяет дублирующиеся IP адреса"""
    print("[ANTIFRAUD] Проверка дубликатов IP...")
    
    ip_users = get_users_by_ip()
    
    for ip, users in ip_users.items():
        # Если 2+ юзера с одного IP
        if len(users) >= 2:
            user_ids = [u['id'] for u in users]
            
            # Проверяем, не игнорируется ли
            if is_ip_ignored(ip, user_ids):
                continue
            
            # Проверяем, не отправляли ли уже алерт
            if is_alert_sent("warning", ip, user_ids):
                continue
            
            # Отправляем предупреждение
            await send_antifraud_alert("warning", users, ip)
            mark_alert_sent("warning", ip, user_ids)
            
    print("[ANTIFRAUD] Проверка завершена")


async def check_promo_fraud(activator_id: int, activator_ip: str, promo_owner_id: int):
    """
    Проверяет мошенничество с промокодами.
    Вызывается при активации промокода.
    
    Банит если:
    - Активатор и владелец промокода с одного IP
    - Или два активатора с одного IP активировали один промокод
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем IP владельца промокода
    cursor.execute("SELECT ip_addresses, username FROM users WHERE id = ?", (promo_owner_id,))
    owner_result = cursor.fetchone()
    
    if not owner_result:
        conn.close()
        return False
    
    owner_ips_json, owner_username = owner_result
    owner_ips = json.loads(owner_ips_json) if owner_ips_json else []
    
    # Получаем данные активатора
    cursor.execute("SELECT username FROM users WHERE id = ?", (activator_id,))
    activator_result = cursor.fetchone()
    activator_username = activator_result[0] if activator_result else None
    
    conn.close()
    
    # Проверяем совпадение IP
    if activator_ip in owner_ips:
        # МОШЕННИЧЕСТВО! Активатор и владелец с одного IP
        users = [
            {'id': activator_id, 'username': activator_username},
            {'id': promo_owner_id, 'username': owner_username}
        ]
        
        # Баним обоих
        ban_users([activator_id, promo_owner_id])
        
        # Отправляем алерт
        await send_antifraud_alert("ban", users, activator_ip)
        
        return True  # Мошенничество обнаружено
    
    return False  # Все ок


async def check_same_ip_promo_activation(activator_id: int, activator_ip: str, promo_id: int):
    """
    Проверяет, активировал ли кто-то другой этот промокод с того же IP.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем всех, кто активировал этот промокод
    cursor.execute("""
        SELECT u.id, u.username, u.ip_addresses 
        FROM users u 
        WHERE u.activated_promocodes LIKE ?
    """, (f'%{promo_id}%',))
    
    activators = cursor.fetchall()
    
    # Получаем username активатора
    cursor.execute("SELECT username FROM users WHERE id = ?", (activator_id,))
    activator_result = cursor.fetchone()
    activator_username = activator_result[0] if activator_result else None
    
    conn.close()
    
    for other_id, other_username, other_ips_json in activators:
        if other_id == activator_id:
            continue
        
        other_ips = json.loads(other_ips_json) if other_ips_json else []
        
        if activator_ip in other_ips:
            # МОШЕННИЧЕСТВО! Два активатора с одного IP
            users = [
                {'id': activator_id, 'username': activator_username},
                {'id': other_id, 'username': other_username}
            ]
            
            # Баним обоих
            ban_users([activator_id, other_id])
            
            # Отправляем алерт
            await send_antifraud_alert("ban", users, activator_ip)
            
            return True
    
    return False


async def antifraud_task():
    """Фоновая задача - проверяет каждые 5 минут"""
    print("[ANTIFRAUD] Запуск фоновой задачи антифрод...")
    
    while True:
        try:
            await check_duplicate_ips()
        except Exception as e:
            print(f"[ANTIFRAUD] Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # Ждем 5 минут
        await asyncio.sleep(300)
