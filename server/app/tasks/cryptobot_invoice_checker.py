"""
CryptoBot Invoice Checker
Проверяет оплату счетов CryptoBot каждые 30 секунд
"""

import asyncio
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
from datetime import datetime
from app.config import DB_PATH, BOT_TOKEN, CRYPTOBOT_API_TOKEN
from aiocryptopay import AioCryptoPay, Networks
from aiogram import Bot
from aiogram.enums import ParseMode

# Bot инициализируется один раз
bot = Bot(token=BOT_TOKEN)

def get_crypto():
    """Получить экземпляр AioCryptoPay"""
    return AioCryptoPay(token=CRYPTOBOT_API_TOKEN, network=Networks.MAIN_NET)

def calculate_stars_from_usdt(usdt_amount: float) -> int:
    """
    Рассчитать количество Stars из USDT с бонусом +5%
    50 Stars = $0.75
    """
    usd_amount = usdt_amount * 1.0  # USDT ~ USD
    
    # 50 stars = $0.75, значит 1 star = $0.015
    stars_base = int(usd_amount / 0.015)
    
    # +5% бонус
    stars_with_bonus = int(stars_base * 1.05)
    
    return stars_with_bonus

async def notify_user(user_id: int, stars_amount: int, usdt_amount: float):
    """Отправить уведомление пользователю о пополнении с картинкой"""
    try:
        caption = (
            f"✅ <b>Обнаружено пополнение</b>\n\n"
            f"<b>{stars_amount} × ⭐</b>\n\n"
            f"Получено: {usdt_amount} USDT"
        )
        
        # Пробуем отправить с картинкой через copy_message из канала
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id="@sleserres",
                message_id=4,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            print(f"✅ Notification with image sent to user {user_id}")
        except Exception as img_e:
            # Fallback на обычное сообщение если не удалось скопировать
            print(f"⚠️ Failed to copy image: {img_e}, sending text only")
            await bot.send_message(
                user_id,
                caption,
                parse_mode=ParseMode.HTML
            )
            print(f"✅ Text notification sent to user {user_id}")
    except Exception as e:
        print(f"Error sending notification to user {user_id}: {e}")

async def check_pending_invoices():
    """Проверить pending счета"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем все pending счета
        cursor.execute(
            "SELECT id, user_id, invoice_id, amount_usdt, amount_stars_expected, expires_at FROM cryptobot_invoices WHERE status = 'pending'"
        )
        pending = cursor.fetchall()
        
        if not pending:
            print("📭 No pending invoices")
            conn.close()
            return
        
        print(f"🔍 Checking {len(pending)} pending invoices...")
        
        for db_id, user_id, invoice_id, amount_usdt, amount_stars_expected, expires_at in pending:
            try:
                # Проверяем истек ли срок
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_dt:
                    print(f"⏰ Invoice {invoice_id} expired")
                    cursor.execute(
                        "UPDATE cryptobot_invoices SET status = 'expired' WHERE id = ?",
                        (db_id,)
                    )
                    conn.commit()
                    continue
                
                # Получаем инвойс через API
                crypto = get_crypto()
                invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
                
                # invoices это список, не объект с .items
                if not invoices or len(invoices) == 0:
                    print(f"⚠️ Invoice {invoice_id} not found")
                    continue
                
                invoice = invoices[0]
                
                # Проверяем статус
                if invoice.status == "paid":
                    print(f"💰 Invoice {invoice_id} is PAID!")
                    
                    # Рассчитываем Stars по фактической сумме
                    paid_amount = float(invoice.paid_amount) if invoice.paid_amount else amount_usdt
                    stars_to_credit = calculate_stars_from_usdt(paid_amount)
                    
                    # Обновляем инвойс
                    cursor.execute(
                        """UPDATE cryptobot_invoices 
                           SET status = 'paid', 
                               confirmed_at = ?,
                               amount_stars_actual = ?
                           WHERE id = ?""",
                        (datetime.now().isoformat(), stars_to_credit, db_id)
                    )
                    
                    # Начисляем Stars пользователю
                    cursor.execute(
                        "UPDATE users SET balance = balance + ? WHERE id = ?",
                        (stars_to_credit, user_id)
                    )
                    
                    conn.commit()
                    
                    print(f"✅ Payment confirmed! User {user_id} received {stars_to_credit} Stars ({paid_amount} USDT)")
                    
                    # Отправляем уведомление
                    await notify_user(user_id, stars_to_credit, paid_amount)
                    
                elif invoice.status in ["expired", "cancelled"]:
                    print(f"❌ Invoice {invoice_id} status: {invoice.status}")
                    cursor.execute(
                        "UPDATE cryptobot_invoices SET status = ? WHERE id = ?",
                        (invoice.status, db_id)
                    )
                    conn.commit()
                
            except Exception as e:
                print(f"Error checking invoice {invoice_id}: {e}")
                import traceback
                traceback.print_exc()
        
        conn.close()
        
    except Exception as e:
        print(f"Error in check_pending_invoices: {e}")
        import traceback
        traceback.print_exc()

async def cryptobot_checker_loop():
    """Основной цикл проверки"""
    print("🚀 CryptoBot Invoice Checker started")
    print(f"Checking every 30 seconds...")
    
    while True:
        try:
            await check_pending_invoices()
        except Exception as e:
            print(f"Error in cryptobot checker loop: {e}")
            import traceback
            traceback.print_exc()
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(cryptobot_checker_loop())
