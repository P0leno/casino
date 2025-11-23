"""
CryptoBot Payment Router
Создание счетов через CryptoPay API
"""

from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
from datetime import datetime, timedelta
from app.config import DB_PATH, BOT_TOKEN, CRYPTOBOT_API_TOKEN
from app.utils.validate import validate_init_data
from aiocryptopay import AioCryptoPay, Networks

router = APIRouter(prefix="/api/cryptobot", tags=["cryptobot"])

# CryptoPay будет инициализироваться в async функциях
def get_crypto():
    """Получить экземпляр AioCryptoPay"""
    return AioCryptoPay(token=CRYPTOBOT_API_TOKEN, network=Networks.MAIN_NET)

class CreateInvoiceRequest(BaseModel):
    initData: str
    usdtAmount: float  # Количество USDT

def get_usdt_rate() -> float:
    """Получить курс USDT/USD (обычно ~1.0)"""
    return 1.0

def calculate_stars_from_usdt(usdt_amount: float) -> int:
    """
    Рассчитать количество Stars из USDT с бонусом +5%
    50 Stars = $0.75
    """
    usd_amount = usdt_amount * get_usdt_rate()
    
    # 50 stars = $0.75, значит 1 star = $0.015
    stars_base = int(usd_amount / 0.015)
    
    # +5% бонус
    stars_with_bonus = int(stars_base * 1.05)
    
    return stars_with_bonus

@router.post("/create-invoice")
async def create_invoice(request: CreateInvoiceRequest):
    """Создать счет CryptoBot для оплаты"""
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
        
        usdt_amount = request.usdtAmount
        
        if usdt_amount < 1:
            return {"success": False, "message": "Минимальная сумма 1 USDT"}
        
        # Рассчитываем Stars с +5% бонусом
        stars_amount = calculate_stars_from_usdt(usdt_amount)
        
        # Создаем счет через CryptoPay
        crypto = get_crypto()
        invoice = await crypto.create_invoice(
            amount=usdt_amount,
            currency_type="crypto",
            asset="USDT",
            description=f"Пополнение баланса (+5% бонус)",
            hidden_message=f"✅ Вы получили {stars_amount} ⭐",
            payload=str(user_id),
            expires_in=1800  # 30 минут
        )
        
        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(seconds=1800)
        
        cursor.execute(
            """INSERT INTO cryptobot_invoices 
               (user_id, invoice_id, amount_usdt, amount_stars_expected, bot_invoice_url, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, invoice.invoice_id, usdt_amount, stars_amount, 
             invoice.bot_invoice_url, datetime.now().isoformat(), expires_at.isoformat())
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ CryptoBot invoice created: invoice_id={invoice.invoice_id}, user_id={user_id}, amount={usdt_amount} USDT -> {stars_amount} Stars")
        
        return {
            "success": True,
            "usdtAmount": usdt_amount,
            "starsAmount": stars_amount,
            "invoiceUrl": invoice.bot_invoice_url,
            "invoiceId": invoice.invoice_id
        }
        
    except Exception as e:
        print(f"Error creating CryptoBot invoice: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": "Ошибка создания счета"}

@router.post("/calculate-stars")
async def calculate_stars(request: CreateInvoiceRequest):
    """Рассчитать количество Stars из USDT с +5% бонусом"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        usdt_amount = request.usdtAmount
        
        if usdt_amount < 1:
            return {"success": False, "message": "Минимальная сумма 1 USDT", "stars": 0}
        
        # Рассчитываем Stars с +5% бонусом
        stars_amount = calculate_stars_from_usdt(usdt_amount)
        
        return {
            "success": True,
            "stars": stars_amount,
            "usdtAmount": usdt_amount,
            "bonusPercent": 5
        }
        
    except Exception as e:
        print(f"Error calculating stars: {e}")
        return {"success": False, "message": "Ошибка расчета", "stars": 0}
