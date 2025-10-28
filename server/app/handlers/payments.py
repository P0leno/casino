from aiogram import Router, F
from aiogram.types import PreCheckoutQuery, Message
import json
import sqlite3
from app.config import DB_PATH

router = Router()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    try:
        payload_data = json.loads(pre_checkout_query.invoice_payload)
        expected_amount = payload_data.get("amount")
        actual_amount = pre_checkout_query.total_amount
        
        # Проверяем что сумма не была подменена
        if expected_amount != actual_amount:
            await pre_checkout_query.answer(
                ok=False, 
                error_message="Сумма платежа была изменена. Попробуйте снова."
            )
            return
        
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        print(f"Error in pre_checkout: {e}")
        await pre_checkout_query.answer(
            ok=False,
            error_message="Ошибка обработки платежа. Попробуйте снова."
        )

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    
    try:
        payload_data = json.loads(payment.invoice_payload)
        user_id = payload_data.get("user_id")
        
        # ВАЖНО: Используем total_amount из payment, а НЕ из payload!
        # Это защищает от подмены суммы в payload
        amount = payment.total_amount
        
        if not user_id or not amount:
            print(f"Invalid payment data: user_id={user_id}, amount={amount}")
            return
        
        # Проверяем что пользователь совпадает с тем, кто оплатил
        if message.from_user.id != user_id:
            print(f"User ID mismatch: expected {user_id}, got {message.from_user.id}")
            await message.answer(
                "❌ Ошибка: несовпадение пользователя. Обратитесь в поддержку."
            )
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            current_balance = result[0] or 0
            new_balance = current_balance + amount
            
            cursor.execute(
                "UPDATE users SET balance = ? WHERE id = ?",
                (new_balance, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, balance) VALUES (?, datetime('now'), ?)",
                (user_id, amount)
            )
            new_balance = amount
        
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ <b>Пополнение успешно!</b>\n\n"
            f"💰 Зачислено: <b>{amount}</b> звезд\n"
            f"📊 Новый баланс: <b>{new_balance}</b> звезд",
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Error processing payment: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке платежа. Обратитесь в поддержку."
        )
