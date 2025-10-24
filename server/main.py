from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hmac
import hashlib
from urllib.parse import parse_qs
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidateRequest(BaseModel):
    initData: str

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
    return {"message": "Hello from Python backend!"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/validate")
async def validate(request: ValidateRequest):
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    return {"valid": is_valid}
