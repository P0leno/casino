from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.crash_game import crash_game
import sqlite3
from app.config import DB_PATH

router = APIRouter(prefix="/api/crash", tags=["crash"])

class BetRequest(BaseModel):
    user_id: int
    amount: float
    username: str
    avatar: str = None

class CashoutRequest(BaseModel):
    user_id: int

class CancelBetRequest(BaseModel):
    user_id: int

@router.get("/state")
async def get_crash_state():
    """Возвращает текущее состояние краш-игры"""
    return crash_game.get_state()

@router.get("/history")
async def get_crash_history():
    """Возвращает полную историю краш-игры"""
    return {
        "history": crash_game.history[-50:]
    }

@router.post("/bet")
async def place_bet(bet: BetRequest):
    """Размещает ставку"""
    # Минимальная ставка 25 звезд
    if bet.amount < 25:
        raise HTTPException(status_code=400, detail="Минимальная ставка 25 звезд")
    
    # Проверяем баланс
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (bet.user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[0] < bet.amount:
            raise HTTPException(status_code=400, detail="Недостаточно средств")
        
        # Снимаем со счета
        new_balance = int(round(result[0] - bet.amount))
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, bet.user_id))
        conn.commit()
        conn.close()
        
        # Размещаем ставку
        result = crash_game.place_bet(bet.user_id, bet.amount, bet.username, bet.avatar)
        return result
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/cashout")
async def cashout(request: CashoutRequest):
    """Забирает выигрыш"""
    result = crash_game.cashout(request.user_id)
    
    if result["success"]:
        # Начисляем выигрыш
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (request.user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = int(round(current_balance + result["winnings"]))
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, request.user_id))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return result

@router.post("/cancel")
async def cancel_bet(request: CancelBetRequest):
    """Отменяет ставку"""
    result = crash_game.cancel_bet(request.user_id)
    
    if result["success"]:
        # Возвращаем деньги
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (request.user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = int(round(current_balance + result["refund"]))
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, request.user_id))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return result
