"""
TON Transaction Checker
Проверяет входящие TON транзакции и начисляет Stars
"""

import asyncio
import aiohttp
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
from datetime import datetime
from app.config import DB_PATH, BOT_TOKEN
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.enums import ParseMode
from app.utils.error_logger import send_error_log

load_dotenv()

# Адрес мерчанта (тот же что в ton_payments.py)
MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y")

# TON API endpoint
TON_API_URL = "https://tonapi.io/v2"

# Последняя проверенная транзакция (lt - logical time)
last_checked_lt = None

# Инициализация бота для уведомлений
bot = Bot(token=BOT_TOKEN)

def get_ton_usd_rate():
    """Получить текущий курс TON/USD из базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        result = cursor.fetchone()
        conn.close()
        if result:
            return float(result[0])
    except Exception as e:
        print(f"Error getting TON rate: {e}")
    return 5.5  # Fallback

def calculate_stars_from_ton(ton_amount: float) -> int:
    """
    Рассчитать количество Stars из TON с бонусом +5%
    50 Stars = $0.75
    """
    ton_usd_rate = get_ton_usd_rate()
    usd_amount = ton_amount * ton_usd_rate
    
    # 50 stars = $0.75, значит 1 star = $0.015
    stars_base = int(usd_amount / 0.015)
    
    # +5% бонус
    stars_with_bonus = int(stars_base * 1.05)
    
    return stars_with_bonus

def convert_address_to_raw(address: str) -> str:
    """
    Конвертировать user-friendly адрес в raw формат (0:hex)
    UQA3XG-I... -> 0:375c6f88...
    """
    # Если адрес уже в raw формате, возвращаем как есть
    if address.startswith("0:") or address.startswith("-1:"):
        return address
    
    # Простая конвертация для базового случая
    # В production лучше использовать библиотеку pytoniq или tonpy
    try:
        import base64
        # Декодируем base64
        decoded = base64.b64decode(address.replace("-", "+").replace("_", "/") + "==")
        # Первый байт - флаги, второй - workchain
        workchain = decoded[1] if len(decoded) > 1 else 0
        # Следующие 32 байта - адрес
        addr_bytes = decoded[2:34] if len(decoded) >= 34 else decoded[2:]
        addr_hex = addr_bytes.hex()
        
        return f"{workchain}:{addr_hex}"
    except Exception as e:
        print(f"Error converting address: {e}, using as is: {address}")
        return address

async def get_transactions(address: str, limit: int = 10):
    """Получить последние транзакции адреса"""
    global last_checked_lt
    
    try:
        # TONAPI требует адрес в любом формате, но проверим оба
        url = f"{TON_API_URL}/blockchain/accounts/{address}/transactions"
        params = {"limit": limit}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    transactions = data.get("transactions", [])
                    print(f"📬 Fetched {len(transactions)} transactions from TONAPI")
                    return transactions
                else:
                    print(f"TON API error: {response.status}, response: {await response.text()}")
                    return []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        import traceback
        traceback.print_exc()
        # Не логируем каждую ошибку API, только критические в main loop
        return []

async def notify_user(user_id: int, stars_amount: int, ton_amount: float):
    """Отправить уведомление пользователю о пополнении"""
    try:
        message = (
            f"✅ <b>Обнаружено пополнение</b>\n\n"
            f"<b>{stars_amount} × ⭐</b>\n\n"
            f"Получено: {ton_amount} TON"
        )
        
        await bot.send_message(
            user_id,
            message,
            parse_mode=ParseMode.HTML
        )
        print(f"✅ Notification sent to user {user_id}")
    except Exception as e:
        print(f"Error sending notification to user {user_id}: {e}")
        await send_error_log(e, f"ton_checker.py: notify_user {user_id}")

async def process_transaction(tx):
    """Обработать входящую транзакцию"""
    try:
        # Получаем все сообщения в транзакции
        in_msg = tx.get("in_msg", {})
        out_msgs = tx.get("out_msgs", [])
        
        # Ищем входящее сообщение с TON
        value = 0
        comment = ""
        
        # Проверяем in_msg
        if in_msg:
            value = int(in_msg.get("value", 0))
            message = in_msg.get("message", "")
            decoded = in_msg.get("decoded_body", {})
            comment = decoded.get("text", message) if decoded else message
        
        # Если нет in_msg, проверяем out_msgs
        if value <= 0 and out_msgs:
            for msg in out_msgs:
                msg_value = int(msg.get("value", 0))
                if msg_value > 0:
                    value = msg_value
                    message = msg.get("message", "")
                    decoded = msg.get("decoded_body", {})
                    comment = decoded.get("text", message) if decoded else message
                    break
        
        if value <= 0:
            print(f"⏭️  Transaction with no value, skipping")
            return
        
        # Конвертируем nanoTON в TON
        ton_amount = value / 1e9
        
        if not comment:
            print(f"💬 Transaction without comment: {ton_amount} TON, tx_hash: {tx.get('hash', 'unknown')}")
            return
        
        # Убираем пробелы
        comment = comment.strip()
        
        print(f"🔍 Found transaction: {ton_amount} TON, comment: '{comment}', tx_hash: {tx.get('hash', 'unknown')[:8]}...")
        
        # Ищем инвойс по коду платежа (регистронезависимо)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔎 Searching invoice for payment_code: '{comment}'")
        
        cursor.execute(
            "SELECT id, user_id, amount_ton, status FROM ton_invoices WHERE UPPER(payment_code) = UPPER(?)",
            (comment,)
        )
        invoice = cursor.fetchone()
        
        if not invoice:
            print(f"❌ Invoice not found for payment_code: '{comment}'")
            # Проверим все pending инвойсы для отладки
            cursor.execute("SELECT payment_code FROM ton_invoices WHERE status = 'pending' ORDER BY created_at DESC LIMIT 5")
            pending = cursor.fetchall()
            if pending:
                codes = [p[0] for p in pending]
                print(f"   Pending payment codes in DB: {codes}")
            conn.close()
            return
        
        invoice_id, user_id, expected_ton, status = invoice
        print(f"✅ Invoice found: id={invoice_id}, user_id={user_id}, expected={expected_ton} TON, status={status}")
        
        if status == 'confirmed':
            print(f"⚠️  Invoice {invoice_id} already confirmed, skipping")
            conn.close()
            return
        
        # Рассчитываем Stars по полученной сумме
        print(f"💰 Calculating Stars: {ton_amount} TON")
        stars_to_credit = calculate_stars_from_ton(ton_amount)
        print(f"⭐ Stars to credit: {stars_to_credit}")
        
        # Получаем tx данные
        tx_hash = tx.get("hash", "")
        tx_lt = str(tx.get("lt", ""))
        tx_timestamp = tx.get("utime", 0)
        
        print(f"💾 Updating database: invoice_id={invoice_id}, tx_hash={tx_hash[:8]}...")
        
        # Обновляем инвойс
        cursor.execute(
            """UPDATE ton_invoices 
               SET status = 'confirmed', 
                   confirmed_at = ?,
                   amount_received = ?,
                   amount_stars_actual = ?,
                   tx_hash = ?,
                   tx_lt = ?,
                   tx_timestamp = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), ton_amount, stars_to_credit, tx_hash, tx_lt, tx_timestamp, invoice_id)
        )
        
        print(f"💳 Crediting {stars_to_credit} Stars to user {user_id}")
        
        # Начисляем Stars пользователю
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (stars_to_credit, user_id)
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Payment confirmed! User {user_id} received {stars_to_credit} Stars ({ton_amount} TON)")
        
        # Отправляем уведомление пользователю
        print(f"📨 Sending notification to user {user_id}...")
        await notify_user(user_id, stars_to_credit, ton_amount)
        
    except Exception as e:
        print(f"Error processing transaction: {e}")
        await send_error_log(e, "ton_checker.py: process_transaction")
        import traceback
        traceback.print_exc()

async def check_new_transactions():
    """Проверить новые транзакции"""
    global last_checked_lt
    
    print(f"🔍 Checking TON transactions for wallet: {MERCHANT_ADDRESS}")
    
    transactions = await get_transactions(MERCHANT_ADDRESS, limit=20)
    
    if not transactions:
        print("📭 No new transactions")
        return
    
    # Сортируем по lt (logical time) в порядке возрастания
    transactions.sort(key=lambda x: int(x.get("lt", 0)))
    
    # Обрабатываем только новые транзакции
    for tx in transactions:
        tx_lt = int(tx.get("lt", 0))
        
        # Пропускаем если уже проверяли
        if last_checked_lt and tx_lt <= last_checked_lt:
            continue
        
        await process_transaction(tx)
        last_checked_lt = tx_lt
    
    # Сохраняем последний lt
    if transactions:
        last_lt = max([int(tx.get("lt", 0)) for tx in transactions])
        if not last_checked_lt or last_lt > last_checked_lt:
            last_checked_lt = last_lt

async def main():
    """Основной цикл проверки"""
    print("🚀 TON Transaction Checker started")
    print(f"Monitoring address: {MERCHANT_ADDRESS}")
    
    while True:
        try:
            await check_new_transactions()
        except Exception as e:
            print(f"Error in main loop: {e}")
            await send_error_log(e, "ton_checker.py: main loop")
            import traceback
            traceback.print_exc()
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
