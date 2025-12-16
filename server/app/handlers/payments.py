from aiogram import Router, F, Bot
from aiogram.types import PreCheckoutQuery, Message
from aiogram.enums import ParseMode
import json
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
from app.config import DB_PATH, SUPPORT_BOT_TOKEN, SUPPORT_GROUP_ID

router = Router()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    try:
        payload_data = json.loads(pre_checkout_query.invoice_payload)
        payment_type = payload_data.get("type")
        
        # Для приоритетной очереди сумма всегда 1 звезда
        if payment_type == "priority":
            if pre_checkout_query.total_amount != 1:
                await pre_checkout_query.answer(
                    ok=False, 
                    error_message="Неверная сумма платежа."
                )
                return
        else:
            # Для обычных пополнений проверяем сумму
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
        payment_type = payload_data.get("type")
        
        # Обработка приоритетной очереди
        if payment_type == "priority":
            dialog_id = payload_data.get("dialog_id")
            user_id = payload_data.get("user_id")
            
            if not dialog_id or not user_id:
                print(f"Invalid priority payment data: dialog_id={dialog_id}, user_id={user_id}")
                return
            
            # Получаем информацию о диалоге
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, category FROM support_dialogs WHERE dialog_id = ?",
                (dialog_id,)
            )
            dialog_info = cursor.fetchone()
            conn.close()
            
            if not dialog_info:
                print(f"Dialog #{dialog_id} not found")
                await message.answer("❌ Диалог не найден")
                return
            
            username, category = dialog_info
            
            # Устанавливаем isPriority = 1
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE support_dialogs SET isPriority = 1 WHERE dialog_id = ?",
                (dialog_id,)
            )
            conn.commit()
            conn.close()
            
            # Получаем список участников группы и отправляем уведомления
            if SUPPORT_BOT_TOKEN and SUPPORT_GROUP_ID:
                try:
                    support_bot = Bot(token=SUPPORT_BOT_TOKEN)
                    
                    # Уведомляем пользователя от бота поддержки
                    await support_bot.send_message(
                        user_id,
                        "✅ <b>Вы купили приоритет!</b>\n\n"
                        "Ищу свободных сотрудников...",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Получаем список админов
                    admins = await support_bot.get_chat_administrators(SUPPORT_GROUP_ID)
                    bot_me = await support_bot.get_me()
                    
                    mentions = []
                    for admin in admins:
                        # Пропускаем бота
                        if admin.user.id == bot_me.id:
                            continue
                        
                        if admin.user.username:
                            mentions.append(f"@{admin.user.username}")
                        else:
                            # Используем mention по ID (только для отображения, не тегает)
                            mentions.append(f"[{admin.user.full_name}](tg://user?id={admin.user.id})")
                    
                    mentions_text = " ".join(mentions)
                    
                    # Отправляем сообщение в группу
                    await support_bot.send_message(
                        SUPPORT_GROUP_ID,
                        f"⭐ <b>ПРИОРИТЕТНАЯ ОЧЕРЕДЬ</b>\n\n"
                        f"Пользователь @{username} (ID: {user_id}) купил приоритет\n"
                        f"Диалог: #{dialog_id}\n"
                        f"Категория: {category}\n\n"
                        f"Сотрудники: {mentions_text}",
                        parse_mode=ParseMode.HTML
                    )
                    
                    await support_bot.session.close()
                    
                except Exception as e:
                    print(f"Error notifying support group: {e}")
            
            return
        
        # Обработка обычного пополнения
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
        
        conn = get_db_connection()
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
        
        # Начисляем 10% владельцу реферального промокода (если есть)
        try:
            # Получаем список активированных промокодов
            cursor.execute("SELECT activated_promocodes FROM users WHERE id = ?", (user_id,))
            promo_result = cursor.fetchone()
            
            if promo_result and promo_result[0]:
                activated_promocodes = json.loads(promo_result[0] or '[]')
                
                if activated_promocodes:
                    # Проверяем какие из промокодов являются реферальными
                    placeholders = ','.join('?' * len(activated_promocodes))
                    cursor.execute(
                        f"SELECT id, owner, type FROM promocodes WHERE id IN ({placeholders}) AND (type = 'ref' OR type = 'refCustom')",
                        activated_promocodes
                    )
                    ref_promo = cursor.fetchone()
                    
                    if ref_promo:
                        promo_id, owner_id, promo_type = ref_promo
                        
                        # Начисляем 10% владельцу на refbalance
                        ref_bonus = int(amount * 0.1)
                        cursor.execute(
                            "UPDATE users SET refbalance = refbalance + ? WHERE id = ?",
                            (ref_bonus, owner_id)
                        )
                        
                        # Логируем в историю промокода (записываем полную сумму пополнения, не бонус)
                        cursor.execute(
                            "INSERT INTO promo_history (promo_id, user_id, action_type, amount) VALUES (?, ?, 'topup', ?)",
                            (promo_id, user_id, amount)
                        )
                        
                        conn.commit()
                        print(f"✅ Начислено {ref_bonus}⭐ рефбонуса владельцу {owner_id} от пополнения {user_id}")
        except Exception as e:
            print(f"Error processing ref bonus: {e}")
        
        conn.close()
        
        # Сообщение не отправляется - баланс обновляется автоматически в WebApp
        
    except Exception as e:
        print(f"Error processing payment: {e}")
        # Ошибку тоже не отправляем в чат
