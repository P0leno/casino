from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import ADMIN_IDS
from app.utils.rate_limit import start_command_rate_limiter

APP_URL = "https://proxmox-bubuntu1.tailcfe40a.ts.net"

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Проверка rate limit: если превышен лимит 6 запросов за 3 минуты - игнорируем
    allowed, remaining_time = start_command_rate_limiter.is_allowed(user_id)
    if not allowed:
        return
    
    if user_id not in ADMIN_IDS:
        await message.answer("<b>Бот находится в разработке</b>", parse_mode="HTML")
    else:
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
