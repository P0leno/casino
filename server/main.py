from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hmac
import hashlib
from urllib.parse import parse_qs
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
import json
import random

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            creation_date TEXT NOT NULL,
            is_banned INTEGER DEFAULT 0,
            last_spin_date TEXT,
            inventory TEXT DEFAULT '[]',
            balance INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_chances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            visible_chance REAL NOT NULL,
            real_chance REAL NOT NULL,
            mode TEXT DEFAULT 'free_spin'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_name TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL
        )
    """)
    
    # Инициализация шансов для подарков
    gifts = [
        ('bear', 10.0, 10.0),
        ('cake', 10.0, 10.0),
        ('cup', 10.0, 10.0),
        ('diamond', 10.0, 5.0),
        ('flowers', 10.0, 10.0),
        ('gift', 10.0, 15.0),
        ('heart', 10.0, 10.0),
        ('ring', 10.0, 5.0),
        ('rocket', 10.0, 5.0),
        ('rose', 10.0, 20.0)
    ]
    
    for gift_name, visible, real in gifts:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_chances (gift_name, visible_chance, real_chance) VALUES (?, ?, ?)",
            (gift_name, visible, real)
        )
    
    # Инициализация цен на подарки
    prices = [
        ('bear', 15),
        ('cake', 50),
        ('cup', 100),
        ('diamond', 100),
        ('flowers', 50),
        ('gift', 25),
        ('heart', 15),
        ('ring', 100),
        ('rocket', 50),
        ('rose', 25)
    ]
    
    for gift_name, price in prices:
        cursor.execute(
            "INSERT OR IGNORE INTO gift_prices (gift_name, price) VALUES (?, ?)",
            (gift_name, price)
        )
    
    conn.commit()
    conn.close()

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidateRequest(BaseModel):
    initData: str

class BanRequest(BaseModel):
    initData: str
    targetUserId: int

class UpdateChanceRequest(BaseModel):
    initData: str
    giftName: str
    visibleChance: float
    realChance: float

class SellGiftRequest(BaseModel):
    initData: str
    giftName: str
    index: int

def validate_init_data(init_data: str, bot_token: str) -> bool:
    try:
        parsed = parse_qs(init_data)
        hash_value = parsed.get('hash', [''])[0]
        
        if not hash_value:
            return False
        
        data_check_string = '\n'.join([f'{k}={v[0]}' for k, v in sorted(parsed.items()) if k != 'hash'])
        secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(hash_value, calculated_hash)
    except Exception:
        return False

@app.get("/")
async def root():
    return {"message": "Welcome to Shell Api"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/validate")
async def validate(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isBanned": False}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "isBanned": False}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            is_banned = bool(result[0])
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, is_banned) VALUES (?, ?, 0)",
                (user_id, datetime.now().isoformat())
            )
            conn.commit()
            is_banned = False
        
        conn.close()
        
        return {"valid": True, "isBanned": is_banned}
    except Exception:
        return {"valid": False, "isBanned": False}

@app.post("/api/check-admin")
async def check_admin(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isAdmin": False}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if user_data:
            user = json.loads(user_data)
            user_id = user.get('id')
            
            is_admin = user_id in ADMIN_IDS
            return {"valid": True, "isAdmin": is_admin}
        
        return {"valid": True, "isAdmin": False}
    except Exception:
        return {"valid": False, "isAdmin": False}

@app.post("/api/ban-user")
async def ban_user(request: BanRequest):
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE id = ?", (request.targetUserId,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (request.targetUserId,))
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, is_banned) VALUES (?, ?, 1)",
                (request.targetUserId, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/unban-user")
async def unban_user(request: BanRequest):
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE id = ?", (request.targetUserId,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (request.targetUserId,))
        else:
            cursor.execute(
                "INSERT INTO users (id, creation_date, is_banned) VALUES (?, ?, 0)",
                (request.targetUserId, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/check-ban")
async def check_ban(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "isBanned": False}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "isBanned": False}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        is_banned = bool(result[0]) if result else False
        return {"valid": True, "isBanned": is_banned}
    except Exception:
        return {"valid": False, "isBanned": False}

@app.post("/api/check-spin-available")
async def check_spin_available(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "available": False, "timeLeft": 0}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "available": False, "timeLeft": 0}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"valid": True, "available": True, "timeLeft": 0}
        
        last_spin = datetime.fromisoformat(result[0])
        next_spin = last_spin + timedelta(hours=24)
        now = datetime.now()
        
        if now >= next_spin:
            return {"valid": True, "available": True, "timeLeft": 0}
        
        time_left = int((next_spin - now).total_seconds())
        return {"valid": True, "available": False, "timeLeft": time_left}
    except Exception as e:
        return {"valid": False, "available": False, "timeLeft": 0}

@app.post("/api/spin")
async def spin(request: ValidateRequest):
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверка доступности спина
        cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_spin = datetime.fromisoformat(result[0])
            if datetime.now() < last_spin + timedelta(hours=24):
                conn.close()
                return {"success": False, "message": "Spin not available yet"}
        
        # Получение шансов
        cursor.execute("SELECT gift_name, real_chance FROM gift_chances")
        chances = cursor.fetchall()
        
        # Выбор подарка на основе реальных шансов
        total = sum(chance[1] for chance in chances)
        rand = random.uniform(0, total)
        current = 0
        selected_gift = chances[0][0]
        
        for gift_name, chance in chances:
            current += chance
            if rand <= current:
                selected_gift = gift_name
                break
        
        # Получение инвентаря
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        inv_result = cursor.fetchone()
        inventory = json.loads(inv_result[0]) if inv_result and inv_result[0] else []
        
        # Добавление подарка
        inventory.append(selected_gift)
        
        # Обновление БД
        cursor.execute(
            "UPDATE users SET last_spin_date = ?, inventory = ? WHERE id = ?",
            (datetime.now().isoformat(), json.dumps(inventory), user_id)
        )
        conn.commit()
        conn.close()
        
        return {"success": True, "gift": selected_gift}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/get-inventory")
async def get_inventory(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "inventory": []}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": True, "inventory": []}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        inventory = json.loads(result[0]) if result and result[0] else []
        return {"valid": True, "inventory": inventory}
    except Exception:
        return {"valid": False, "inventory": []}

@app.post("/api/sell-gift")
async def sell_gift(request: SellGiftRequest):
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем инвентарь и баланс
        cursor.execute("SELECT inventory, balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        inventory = json.loads(result[0]) if result[0] else []
        balance = result[1] or 0
        
        # Проверяем, есть ли подарок в инвентаре
        if request.index < 0 or request.index >= len(inventory):
            conn.close()
            return {"success": False, "message": "Invalid index"}
        
        if inventory[request.index] != request.giftName:
            conn.close()
            return {"success": False, "message": "Gift mismatch"}
        
        # Получаем цену подарка
        cursor.execute("SELECT price FROM gift_prices WHERE gift_name = ?", (request.giftName,))
        price_result = cursor.fetchone()
        
        if not price_result:
            conn.close()
            return {"success": False, "message": "Price not found"}
        
        price = price_result[0]
        
        # Удаляем подарок из инвентаря
        inventory.pop(request.index)
        
        # Обновляем баланс
        new_balance = balance + price
        
        # Сохраняем в БД
        cursor.execute(
            "UPDATE users SET inventory = ?, balance = ? WHERE id = ?",
            (json.dumps(inventory), new_balance, user_id)
        )
        conn.commit()
        conn.close()
        
        return {"success": True, "newBalance": new_balance, "price": price}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/get-balance")
async def get_balance(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "balance": 0}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "balance": 0}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        balance = result[0] if result and result[0] is not None else 0
        return {"valid": True, "balance": balance}
    except Exception as e:
        return {"valid": False, "balance": 0}

@app.post("/api/get-prices")
async def get_prices(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "prices": {}}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, price FROM gift_prices")
        results = cursor.fetchall()
        conn.close()
        
        prices = {gift_name: price for gift_name, price in results}
        return {"valid": True, "prices": prices}
    except Exception as e:
        return {"valid": False, "prices": {}}

@app.post("/api/get-chances")
async def get_chances(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    
    if not is_valid:
        return {"valid": False, "chances": []}
    
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        
        if not user_data:
            return {"valid": False, "chances": []}
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        if user_id not in ADMIN_IDS:
            return {"valid": False, "chances": []}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT gift_name, visible_chance, real_chance FROM gift_chances")
        results = cursor.fetchall()
        conn.close()
        
        chances = [{"name": r[0], "visible": r[1], "real": r[2]} for r in results]
        return {"valid": True, "chances": chances}
    except Exception:
        return {"valid": False, "chances": []}

@app.post("/api/update-chances")
async def update_chances(request: UpdateChanceRequest):
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
        
        if user_id not in ADMIN_IDS:
            return {"success": False, "message": "Not authorized"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_chances SET visible_chance = ?, real_chance = ? WHERE gift_name = ?",
            (request.visibleChance, request.realChance, request.giftName)
        )
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
