import traceback
import sys
from app.config import LOG_BOT_TOKEN, LOGS_ID

async def send_error_log(e: Exception, context: str = ""):
    """
    Отправляет лог ошибки в Telegram канал логов.
    
    Args:
        e: Объект исключения
        context: Описание контекста (где произошла ошибка)
    """
    if not LOG_BOT_TOKEN or not LOGS_ID:
        return

    try:
        from app.log_bot import send_message_to_logs
        
        # Получаем полную информацию об ошибке
        tb = traceback.format_exc()
        
        # Формируем сообщение
        message = (
            f"❌ <b>Ошибка в системе</b>\n\n"
            f"📍 <b>Контекст:</b> {context}\n"
            f"⚠️ <b>Тип:</b> {type(e).__name__}\n"
            f"📝 <b>Сообщение:</b> {str(e)}\n\n"
            f"🔎 <b>Stackpath:</b>\n"
            f"<pre><code class='language-python'>{tb[:3500]}</code></pre>"  # Обрезаем если слишком длинное
        )
        
        await send_message_to_logs(message)
        
    except Exception as log_error:
        print(f"⚠️ Не удалось отправить лог в канал: {log_error}")
