from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import asyncio
from app.config import BOT_TOKEN
from app.utils import validate_init_data
from app.utils.rate_limit import invoice_rate_limiter
from app.bot import bot

router = APIRouter(prefix="/api", tags=["payments"])

class TopUpRequest(BaseModel):
    initData: str
    amount: int

@router.post("/create-invoice")
async def create_invoice(request: TopUpRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "message": "User data not found"}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        # Rate limit: 5 счетов за 3 минуты
        allowed, remaining_time = invoice_rate_limiter.is_allowed(user_id)
        if not allowed:
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            wait_msg = f"Попробуйте через {minutes}м {seconds}с" if minutes > 0 else f"Попробуйте через {seconds}с"
            return {
                "success": False, 
                "message": f"Слишком много запросов. {wait_msg}",
                "rateLimited": True,
                "remainingTime": remaining_time
            }
        
        if request.amount < 1 or request.amount > 2500:
            return {"success": False, "message": "Amount must be between 1 and 2500"}
        
        # Создаем invoice link для Telegram Stars
        title = f"Пополнение баланса"
        description = f"Пополнение на {request.amount} звезд"
        payload = json.dumps({"user_id": user_id, "amount": request.amount})
        currency = "XTR"  # Telegram Stars
        
        # Цены в Telegram Stars (1 star = 1 XTR)
        prices = [{"label": f"{request.amount} звезд", "amount": request.amount}]
        
        # Создаем invoice link
        invoice_link = await bot.create_invoice_link(
            title=title,
            description=description,
            payload=payload,
            currency=currency,
            prices=prices
        )
        
        return {
            "success": True,
            "invoiceUrl": invoice_link
        }
        
    except Exception as e:
        print(f"Error creating invoice: {e}")
        return {"success": False, "message": str(e)}
