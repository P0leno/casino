from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs, quote
import json
from app.utils.database import get_db_connection, DB_PATH
from app.utils.error_logger import send_error_log
import sqlite3
from datetime import datetime
import random
import string
import qrcode
import io
import base64
from app.config import BOT_TOKEN, DB_PATH
from app.utils.validate import validate_init_data

router = APIRouter(prefix="/api/ton", tags=["ton"])

# Адрес мерчанта для получения платежей (замените на свой Tonkeeper адрес)
# Получите адрес в Tonkeeper: Receive → Copy address
MERCHANT_ADDRESS = "UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y"  # ЗАМЕНИТЕ НА СВОЙ

class CreatePaymentRequest(BaseModel):
    initData: str
    tonAmount: float  # Количество TON (не Stars!)

def generate_payment_code():
    """Генерирует уникальный 8-значный код"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_ton_usd_rate():
    """Получить текущий курс TON/USD из базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        result = cursor.fetchone()
        conn.close()
        if result:
            return float(result[0])
    except Exception as e:
        # get_ton_usd_rate is synchronous and often called from async context or sync.
        # It's a helper. We can't await here easily if it's called synchronously.
        # But wait, it's called from `calculate_stars_from_ton` which is sync.
        # And `calculate_stars_from_ton` is called from async handlers.
        # We should probably just print here or use asyncio.run? NO.
        # Let's simple print for this helper to avoid async complexity in sync function.
        # Or better: check if we can make it async? No, that would require refactoring callers.
        # Given it's a small helper, maybe skip send_error_log here or use create_task?
        # We can't use create_task without a loop.
        # Let's skip send_error_log for this specific sync helper fallback.
        print(f"Error getting TON rate: {e}")
        pass
    return 5.5  # Fallback курс

def calculate_stars_from_ton(ton_amount: float) -> int:
    """
    Рассчитать количество Stars из TON с бонусом +5%
    50 Stars = $0.75
    """
    ton_usd_rate = get_ton_usd_rate()
    usd_amount = ton_amount * ton_usd_rate
    
    # 50 stars = $0.75, значит 1 star = $0.015
    stars_base = int(usd_amount / 0.015)
    
    # +5% бонус
    stars_with_bonus = int(stars_base * 1.05)
    
    return stars_with_bonus

def generate_qr_code(data: str) -> str:
    """Генерирует QR код и возвращает base64"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем в base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"

@router.post("/create-payment")
async def create_payment(request: CreatePaymentRequest):
    """Создает платеж TON - генерирует QR код и deep link"""
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
        
        ton_amount = request.tonAmount
        
        if ton_amount < 0.1:
            return {"success": False, "message": "Минимальная сумма 0.1 TON"}
        
        # Рассчитываем Stars с +5% бонусом
        stars_amount = calculate_stars_from_ton(ton_amount)
        
        # Генерируем уникальный payment код (комментарий)
        payment_code = generate_payment_code()
        
        # Создаем таблицу payments если не существует
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ton_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_code TEXT UNIQUE NOT NULL,
                amount_ton REAL NOT NULL,
                amount_stars_expected INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                amount_received REAL,
                amount_stars_actual INTEGER,
                tx_hash TEXT,
                tx_lt TEXT,
                tx_timestamp INTEGER
            )
        """)
        
        cursor.execute(
            """INSERT INTO ton_invoices 
               (user_id, payment_code, amount_ton, amount_stars_expected, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, payment_code, ton_amount, stars_amount, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
        
        # Конвертируем в nanoTON
        amount_nano = int(ton_amount * 1e9)
        
        # Формируем deep link (ton:// работает для всех кошельков)
        # tonkeeper:// специфичен для Tonkeeper
        comment_encoded = quote(payment_code)
        deep_link_ton = f"ton://transfer/{MERCHANT_ADDRESS}?amount={amount_nano}&text={comment_encoded}"
        deep_link_tonkeeper = f"tonkeeper://transfer/{MERCHANT_ADDRESS}?amount={amount_nano}&text={comment_encoded}"
        
        # Генерируем QR код с ton:// ссылкой
        qr_code_base64 = generate_qr_code(deep_link_ton)
        
        print(f"✅ TON payment created: user={user_id}, code={payment_code}, amount={ton_amount} TON -> {stars_amount} Stars")
        
        return {
            "success": True,
            "tonAmount": ton_amount,
            "starsAmount": stars_amount,
            "paymentCode": payment_code,
            "merchantAddress": MERCHANT_ADDRESS,
            "qrCode": qr_code_base64,
            "deepLinkTon": deep_link_ton,
            "deepLinkTonkeeper": deep_link_tonkeeper
        }
        
    except Exception as e:
        print(f"Error creating payment: {e}")
        await send_error_log(e, "ton_payments.py: create_payment")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": "Ошибка создания платежа"}

@router.post("/calculate-stars")
async def calculate_stars(request: CreatePaymentRequest):
    """Рассчитать количество Stars из TON с +5% бонусом"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        ton_amount = request.tonAmount
        
        if ton_amount < 0.1:
            return {"success": False, "message": "Минимальная сумма 0.1 TON", "stars": 0}
        
        # Рассчитываем Stars с +5% бонусом
        stars_amount = calculate_stars_from_ton(ton_amount)
        ton_usd_rate = get_ton_usd_rate()
        usd_amount = ton_amount * ton_usd_rate
        
        return {
            "success": True,
            "stars": stars_amount,
            "tonAmount": ton_amount,
            "usdAmount": round(usd_amount, 2),
            "tonUsdRate": ton_usd_rate,
            "bonusPercent": 5
        }
        
    except Exception as e:
        print(f"Error calculating stars: {e}")
        await send_error_log(e, "ton_payments.py: calculate_stars")
        return {"success": False, "message": "Ошибка расчета", "stars": 0}
