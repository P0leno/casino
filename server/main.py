from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hmac
import hashlib
from urllib.parse import parse_qs
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import json

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
            is_banned INTEGER DEFAULT 0
        )
    """)
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
