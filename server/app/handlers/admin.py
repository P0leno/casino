from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith("confirm_gift_"))
async def confirm_gift_handler(callback: CallbackQuery):
    """Обработчик подтверждения ручной выдачи подарка"""
    try:
        # Парсим callback_data: confirm_gift_{user_id}_{gift_id}
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        user_id = parts[2]
        gift_id = parts[3]
        
        # Удаляем сообщение
        await callback.message.delete()
        
        # Подтверждаем действие
        await callback.answer("✅ Запрос подтвержден и удален")
        
    except Exception as e:
        print(f"Error in confirm_gift_handler: {e}")
        await callback.answer("Ошибка при обработке")
