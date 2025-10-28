from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import parse_qs
import json
import sqlite3
from app.config import BOT_TOKEN, ADMIN_IDS, DB_PATH
from app.utils import validate_init_data

router = APIRouter(prefix="/api", tags=["admin"])

class ValidateRequest(BaseModel):
    initData: str

class UpdateChanceRequest(BaseModel):
    initData: str
    giftName: str
    visibleChance: float
    realChance: float
    pawMin: int = 0
    pawMax: int = 0

@router.post("/get-chances")
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
        cursor.execute("SELECT gift_name, visible_chance, real_chance, paw_min, paw_max FROM gift_chances")
        results = cursor.fetchall()
        conn.close()
        
        chances = [{"name": r[0], "visible": r[1], "real": r[2], "pawMin": r[3] or 0, "pawMax": r[4] or 0} for r in results]
        return {"valid": True, "chances": chances}
    except Exception:
        return {"valid": False, "chances": []}

@router.post("/update-chances")
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
        
        # Валидация pawMin и pawMax на сервере
        paw_min = max(0, min(100, request.pawMin))
        paw_max = max(0, min(100, request.pawMax))
        
        # Проверка что min <= max
        if paw_min > paw_max and paw_max > 0:
            paw_min, paw_max = paw_max, paw_min
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_chances SET visible_chance = ?, real_chance = ?, paw_min = ?, paw_max = ? WHERE gift_name = ?",
            (request.visibleChance, request.realChance, paw_min, paw_max, request.giftName)
        )
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error in update_chances: {e}")
        return {"success": False, "message": "Ошибка сервера"}
