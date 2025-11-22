from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
from datetime import datetime
import random
import string
from app.config import BOT_TOKEN, DB_PATH
from app.utils.validate import validate_init_data

router = APIRouter(prefix="/api/ton", tags=["ton"])

# Адрес мерчанта для получения платежей (замените на свой Tonkeeper адрес)
# Получите адрес в Tonkeeper: Receive → Copy address
MERCHANT_ADDRESS = "UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y"  # ЗАМЕНИТЕ НА СВОЙ

class ConnectWalletRequest(BaseModel):
    initData: str
    walletAddress: str | None

class CreatePaymentRequest(BaseModel):
    initData: str
    amount: int  # Количество звезд

def generate_payment_code():
    """Генерирует уникальный 16-значный код"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

@router.post("/connect-wallet")
async def connect_wallet(request: ConnectWalletRequest):
    """Сохраняет адрес TON кошелька пользователя"""
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
        
        # Сохраняем адрес кошелька в БД
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET ton_wallet_address = ? WHERE id = ?",
            (request.walletAddress, user_id)
        )
        
        conn.commit()
        conn.close()
        
        if request.walletAddress:
            print(f"✅ TON wallet connected: user={user_id}, address={request.walletAddress[:8]}...")
            return {"success": True, "message": "Кошелек подключен"}
        else:
            print(f"✅ TON wallet disconnected: user={user_id}")
            return {"success": True, "message": "Кошелек отключен"}
        
    except Exception as e:
        print(f"Error connecting wallet: {e}")
        return {"success": False, "message": "Ошибка подключения кошелька"}

@router.post("/create-payment")
async def create_payment(request: CreatePaymentRequest):
    """Создает платеж TON - генерирует код и сохраняет в payments"""
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
        
        # Проверяем что кошелек подключен
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT ton_wallet_address FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return {"success": False, "message": "Сначала подключите кошелек"}
        
        wallet_address = result[0]
        
        # Рассчитываем сумму в TON
        # 50 звезд = $0.75
        stars_in_usd = (request.amount / 50) * 0.75
        
        # TODO: Получить актуальный курс TON/USD через API
        # Пока используем примерный курс ~$5.5 за 1 TON
        ton_rate = 5.5
        ton_amount = stars_in_usd / ton_rate
        
        # Генерируем уникальный payment код
        payment_code = generate_payment_code()
        
        # Создаем таблицу payments если не существует
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_code TEXT UNIQUE NOT NULL,
                payment_method TEXT NOT NULL,
                amount_stars INTEGER NOT NULL,
                amount_ton REAL,
                amount_usd REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                tx_hash TEXT
            )
        """)
        
        cursor.execute(
            """INSERT INTO payments 
               (user_id, payment_code, payment_method, amount_stars, amount_ton, amount_usd, created_at)
               VALUES (?, ?, 'ton', ?, ?, ?, ?)""",
            (user_id, payment_code, request.amount, ton_amount, stars_in_usd, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ TON payment created: user={user_id}, code={payment_code}, amount={ton_amount} TON")
        
        return {
            "success": True,
            "tonAmount": ton_amount,
            "usdAmount": stars_in_usd,
            "paymentCode": payment_code,
            "walletAddress": wallet_address,
            "merchantAddress": MERCHANT_ADDRESS  # Адрес для отправки платежа
        }
        
    except Exception as e:
        print(f"Error creating payment: {e}")
        return {"success": False, "message": "Ошибка создания платежа"}

@router.post("/get-wallet")
async def get_wallet(request: BaseModel):
    """Получает сохраненный адрес кошелька"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"success": False, "wallet": None}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"success": False, "wallet": None}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT ton_wallet_address FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        wallet = result[0] if result and result[0] else None
        
        return {"success": True, "wallet": wallet}
        
    except Exception as e:
        print(f"Error getting wallet: {e}")
        return {"success": False, "wallet": None}
