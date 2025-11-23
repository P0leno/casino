"""
TON Transaction Checker
Проверяет входящие TON транзакции и начисляет Stars
"""

import asyncio
import aiohttp
import sqlite3
from datetime import datetime
from app.config import DB_PATH
import os
from dotenv import load_dotenv

load_dotenv()

# Адрес мерчанта (тот же что в ton_payments.py)
MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y")

# TON API endpoint
TON_API_URL = "https://tonapi.io/v2"

# Последняя проверенная транзакция (lt - logical time)
last_checked_lt = None

def get_ton_usd_rate():
    """Получить текущий курс TON/USD из базы данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
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

async def get_transactions(address: str, limit: int = 10):
    """Получить последние транзакции адреса"""
    global last_checked_lt
    
    try:
        url = f"{TON_API_URL}/blockchain/accounts/{address}/transactions"
        params = {"limit": limit}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("transactions", [])
                else:
                    print(f"TON API error: {response.status}")
                    return []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []

def process_transaction(tx):
    """Обработать входящую транзакцию"""
    try:
        # Проверяем что это входящая транзакция
        in_msg = tx.get("in_msg", {})
        if not in_msg:
            return
        
        # Получаем данные транзакции
        value = int(in_msg.get("value", 0))
        if value <= 0:
            return
        
        # Конвертируем nanoTON в TON
        ton_amount = value / 1e9
        
        # Получаем комментарий
        message = in_msg.get("message", "")
        decoded_message = in_msg.get("decoded_body", {})
        comment = decoded_message.get("text", message) if decoded_message else message
        
        if not comment:
            print(f"Transaction without comment: {ton_amount} TON")
            return
        
        # Убираем пробелы
        comment = comment.strip()
        
        print(f"Found transaction: {ton_amount} TON, comment: {comment}")
        
        # Ищем инвойс по коду платежа
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, user_id, amount_ton, status FROM ton_invoices WHERE payment_code = ?",
            (comment,)
        )
        invoice = cursor.fetchone()
        
        if not invoice:
            print(f"Invoice not found for payment_code: {comment}")
            conn.close()
            return
        
        invoice_id, user_id, expected_ton, status = invoice
        
        if status == 'confirmed':
            print(f"Invoice {invoice_id} already confirmed")
            conn.close()
            return
        
        # Рассчитываем Stars по полученной сумме
        stars_to_credit = calculate_stars_from_ton(ton_amount)
        
        # Получаем tx данные
        tx_hash = tx.get("hash", "")
        tx_lt = str(tx.get("lt", ""))
        tx_timestamp = tx.get("utime", 0)
        
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
        
        # Начисляем Stars пользователю
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (stars_to_credit, user_id)
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Payment confirmed! User {user_id} received {stars_to_credit} Stars ({ton_amount} TON)")
        
        # TODO: Отправить уведомление пользователю через бота
        
    except Exception as e:
        print(f"Error processing transaction: {e}")
        import traceback
        traceback.print_exc()

async def check_new_transactions():
    """Проверить новые транзакции"""
    global last_checked_lt
    
    print(f"Checking transactions for {MERCHANT_ADDRESS}...")
    
    transactions = await get_transactions(MERCHANT_ADDRESS, limit=20)
    
    if not transactions:
        return
    
    # Сортируем по lt (logical time) в порядке возрастания
    transactions.sort(key=lambda x: int(x.get("lt", 0)))
    
    # Обрабатываем только новые транзакции
    for tx in transactions:
        tx_lt = int(tx.get("lt", 0))
        
        # Пропускаем если уже проверяли
        if last_checked_lt and tx_lt <= last_checked_lt:
            continue
        
        process_transaction(tx)
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
            import traceback
            traceback.print_exc()
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
