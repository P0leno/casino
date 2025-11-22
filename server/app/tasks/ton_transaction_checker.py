"""
Скрипт для проверки TON транзакций
Проверяет блокчейн TON на наличие входящих транзакций с payment кодами
"""

import asyncio
import aiohttp
import sqlite3
from datetime import datetime
from app.config import DB_PATH

# Адрес кошелька для получения пополнений (raw формат 0:hex)
# Соответствует UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y
MERCHANT_WALLET = "0:c6f8822e54af557ad07c8947ede1a6af013d4e4b2066a13f62a5687d3d408de5"

# TON API endpoint (можно использовать toncenter.com API)
TON_API_URL = "https://toncenter.com/api/v2"
TON_API_KEY = "ab1e62e638eb8976f95dba921d5d474f659781663ef27743e3f5bc1b3843f0b3"  # Получить на https://toncenter.com/

async def check_ton_transactions():
    """Проверяет новые транзакции в TON блокчейне"""
    
    try:
        # Получаем последние транзакции кошелька
        async with aiohttp.ClientSession() as session:
            url = f"{TON_API_URL}/getTransactions"
            params = {
                "address": MERCHANT_WALLET,
                "limit": 10,
                "api_key": TON_API_KEY
            }
            
            print(f"🔍 Checking TON transactions for wallet: {MERCHANT_WALLET[:8]}...")
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"⚠️ TON API error: {response.status}")
                    return
                
                data = await response.json()
                transactions = data.get("result", [])
                
                if not transactions:
                    print("📭 No new transactions")
                    return
                
                print(f"📬 Found {len(transactions)} transactions to check")
                
                # Проверяем каждую транзакцию
                for tx in transactions:
                    await process_transaction(tx)
                    
    except Exception as e:
        print(f"❌ Error checking TON transactions: {e}")
        import traceback
        traceback.print_exc()

async def process_transaction(tx):
    """Обрабатывает одну транзакцию"""
    
    try:
        # Извлекаем данные транзакции
        tx_hash = tx.get("transaction_id", {}).get("hash")
        in_msg = tx.get("in_msg", {})
        
        if not in_msg:
            return
        
        # Получаем точную сумму
        value_nanotons = int(in_msg.get("value", 0))
        value_ton = value_nanotons / 1e9
        
        if value_ton <= 0:
            return
        
        print(f"  💰 TX {tx_hash[:8] if tx_hash else 'unknown'}: {value_ton} TON ({value_nanotons} nanotons)")
        
        # Ищем платеж по точной сумме в nanotons
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем pending платежи за последние 15 минут
        from datetime import datetime, timedelta
        time_threshold = (datetime.now() - timedelta(minutes=15)).isoformat()
        
        cursor.execute(
            """SELECT id, user_id, amount_stars, amount_ton, payment_code, created_at 
               FROM payments 
               WHERE payment_method = 'ton' 
               AND status = 'pending' 
               AND created_at > ?
               ORDER BY created_at DESC""",
            (time_threshold,)
        )
        
        payments = cursor.fetchall()
        
        if not payments:
            conn.close()
            print(f"  ⚠️ No pending TON payments")
            return
        
        # Ищем платеж с совпадающей суммой
        matched_payment = None
        for payment in payments:
            payment_id, user_id, amount_stars, amount_ton, payment_code, created_at = payment
            
            expected_nanotons = int(amount_ton * 1e9)
            
            # Точное совпадение (±5 nanotons на округление)
            if abs(value_nanotons - expected_nanotons) <= 5:
                matched_payment = payment
                print(f"  ✓ Matched: code={payment_code}, expected={expected_nanotons}, got={value_nanotons}")
                break
        
        if not matched_payment:
            conn.close()
            print(f"  ⚠️ No matching payment for {value_nanotons} nanotons")
            return
        
        payment_id, user_id, amount_stars, amount_ton, payment_code, created_at = matched_payment
        
        # Подтверждаем платеж
        cursor.execute(
            """UPDATE payments 
               SET status = 'confirmed', confirmed_at = ?, tx_hash = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), tx_hash, payment_id)
        )
        
        # Начисляем баланс
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            current_balance = result[0] or 0
            new_balance = current_balance + amount_stars
            
            cursor.execute(
                "UPDATE users SET balance = ? WHERE id = ?",
                (new_balance, user_id)
            )
            
            conn.commit()
            print(f"✅ Confirmed: user={user_id}, +{amount_stars} stars, code={payment_code}, tx={tx_hash[:8] if tx_hash else 'unknown'}...")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def ton_transaction_loop():
    """Основной цикл проверки транзакций"""
    print("✅ Запущен мониторинг TON транзакций")
    
    while True:
        try:
            await check_ton_transactions()
            # Проверяем каждые 30 секунд
            await asyncio.sleep(30)
        except Exception as e:
            print(f"❌ Error in TON transaction loop: {e}")
            await asyncio.sleep(60)  # При ошибке ждем минуту

if __name__ == "__main__":
    # Для тестирования
    asyncio.run(ton_transaction_loop())
