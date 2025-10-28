from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import ADMIN_IDS

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("<b>Бот находится в разработке</b>", parse_mode="HTML")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Открыть",
                        web_app=WebAppInfo(url="https://shelloch.xyz")
                    )
                ]
            ]
        )
        await message.answer(
            "<b>Приветствую в SHell</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
