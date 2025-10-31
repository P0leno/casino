"""
Background task для отправки уведомлений о доступности фри спина
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import BOT_TOKEN, DB_PATH

async def check_and_send_spin_notifications():
    """
    Проверяет пользователей у которых спин стал доступен
    и отправляет им уведомления
    """
    bot = Bot(token=BOT_TOKEN)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем всех пользователей у которых:
        # 1. Прошло 24 часа с последнего спина
        # 2. Еще не отправлено уведомление для этого спина
        now = datetime.now()
        cutoff_time = now - timedelta(hours=24)
        
        cursor.execute("""
            SELECT id, last_spin_date, last_spin_notification
            FROM users
            WHERE is_banned = 0
        """)
        
        users = cursor.fetchall()
        notifications_sent = 0
        
        for user_id, last_spin_date, last_notification in users:
            try:
                # Проверяем доступность спина
                spin_available = False
                
                if last_spin_date is None:
                    # Никогда не крутил - спин доступен
                    spin_available = True
                else:
                    last_spin = datetime.fromisoformat(last_spin_date)
                    # Проверяем что прошло 24 часа
                    if now >= last_spin + timedelta(hours=24):
                        spin_available = True
                
                if spin_available:
                    # Проверяем что уведомление еще не отправлялось недавно
                    should_notify = False
                    
                    if last_notification is None:
                        should_notify = True
                    else:
                        last_notif = datetime.fromisoformat(last_notification)
                        # Уведомление было больше 23 часов назад
                        if now >= last_notif + timedelta(hours=23):
                            should_notify = True
                    
                    if should_notify:
                        # Получаем информацию о пользователе
                        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                        if cursor.fetchone():
                            # Отправляем уведомление
                            try:
                                # Получаем имя пользователя из Telegram
                                try:
                                    user_info = await bot.get_chat(user_id)
                                    first_name = user_info.first_name
                                except:
                                    first_name = "Игрок"
                                
                                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(
                                        text="🎁 Крутить кейс",
                                        web_app=WebAppInfo(url="https://shelloch.xyz")
                                    )]
                                ])
                                
                                await bot.send_message(
                                    user_id,
                                    f"🎁 <b>{first_name}</b>, твой бесплатный кейс уже ждет тебя!",
                                    parse_mode="HTML",
                                    reply_markup=keyboard
                                )
                                
                                # Обновляем время последнего уведомления
                                cursor.execute(
                                    "UPDATE users SET last_spin_notification = ? WHERE id = ?",
                                    (now.isoformat(), user_id)
                                )
                                conn.commit()
                                
                                notifications_sent += 1
                                print(f"✅ Отправлено уведомление пользователю {user_id}")
                                
                            except Exception as e:
                                print(f"❌ Ошибка отправки уведомления {user_id}: {e}")
                
            except Exception as e:
                print(f"❌ Ошибка обработки пользователя {user_id}: {e}")
                continue
        
        conn.close()
        print(f"✅ Отправлено уведомлений: {notifications_sent}")
        
    except Exception as e:
        print(f"❌ Ошибка в check_and_send_spin_notifications: {e}")
    finally:
        await bot.session.close()

async def spin_notification_loop():
    """
    Бесконечный цикл проверки уведомлений каждые 10 минут
    """
    while True:
        try:
            await check_and_send_spin_notifications()
        except Exception as e:
            print(f"❌ Ошибка в spin_notification_loop: {e}")
        
        # Ждем 10 минут перед следующей проверкой
        await asyncio.sleep(600)
