from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import ADMIN_IDS
from app.utils.rate_limit import start_command_rate_limiter
from app.utils.database import get_db_connection

APP_URL = "https://proxmox-bubuntu1.tailcfe40a.ts.net"

router = Router()


def _get_setting(key: str, default: str = "") -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default
    except:
        return default


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    allowed, remaining_time = start_command_rate_limiter.is_allowed(user_id)
    if not allowed:
        return

    maintenance = _get_setting("maintenance_mode", "0") == "1"

    if maintenance:
        reason = _get_setting("maintenance_reason", "Сервер временно недоступен")
        await message.answer(
            f"<b>🔧 Ведутся технические работы</b>\n\n{reason}",
            parse_mode="HTML"
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть",
                    web_app=WebAppInfo(url=APP_URL)
                )
            ]
        ]
    )
    await message.answer(
        "<b>Приветствую в SHell</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
