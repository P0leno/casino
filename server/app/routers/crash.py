from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.crash_game import crash_game
import sqlite3
from app.config import DB_PATH, BOT_TOKEN
from app.utils.validate import validate_init_data
from app.utils.balance import get_user_balance
from urllib.parse import parse_qs
import json
import asyncio
from typing import List

router = APIRouter(prefix="/api/crash", tags=["crash"])

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket подключен. Всего: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WebSocket отключен. Осталось: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Отправка сообщения всем подключенным клиентам"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Ошибка отправки в WebSocket: {e}")
                disconnected.append(connection)
        
        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

class BetRequest(BaseModel):
    initData: str
    amount: float

class CashoutRequest(BaseModel):
    initData: str

class CancelBetRequest(BaseModel):
    initData: str

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
    # Проверяем initData
    is_valid = validate_init_data(bet.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")
    
    # Извлекаем данные пользователя из initData
    try:
        parsed = parse_qs(bet.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
        username = user.get('username') or user.get('first_name', 'User')
        avatar = user.get('photo_url')
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user data")
    
    # Минимальная ставка 25 звезд
    if bet.amount < 25:
        raise HTTPException(status_code=400, detail="Минимальная ставка 25 звезд")
    
    # Проверяем баланс
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[0] < bet.amount:
            raise HTTPException(status_code=400, detail="Недостаточно средств")
        
        # Снимаем со счета
        new_balance = int(round(result[0] - bet.amount))
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()
        conn.close()
        
        # Размещаем ставку
        result = crash_game.place_bet(user_id, bet.amount, username, avatar)
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        result.update(user_balance)
        
        return result
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/cashout")
async def cashout(request: CashoutRequest):
    """Забирает выигрыш"""
    # Проверяем initData
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")
    
    # Извлекаем user_id из initData
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user data")
    
    result = crash_game.cashout(user_id)
    
    if result["success"]:
        # Начисляем выигрыш
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = int(round(current_balance + result["winnings"]))
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
            conn.commit()
            conn.close()
            
            # Получаем обновленный баланс
            user_balance = get_user_balance(user_id)
            result.update(user_balance)
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return result

@router.post("/cancel")
async def cancel_bet(request: CancelBetRequest):
    """Отменяет ставку"""
    # Проверяем initData
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")
    
    # Извлекаем user_id из initData
    try:
        parsed = parse_qs(request.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user data")
    
    result = crash_game.cancel_bet(user_id)
    
    if result["success"]:
        # Возвращаем деньги
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = int(round(current_balance + result["refund"]))
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return result

@router.websocket("/ws")
async def websocket_crash(websocket: WebSocket):
    """WebSocket endpoint для краш игры"""
    await manager.connect(websocket)
    
    try:
        # Отправляем начальное состояние
        initial_state = crash_game.get_state()
        await websocket.send_json(initial_state)
        
        # Фоновая задача для отправки обновлений
        async def send_updates():
            while True:
                try:
                    state = crash_game.get_state()
                    await websocket.send_json(state)
                    await asyncio.sleep(0.05)  # 20 обновлений в секунду
                except Exception:
                    break
        
        update_task = asyncio.create_task(send_updates())
        
        # Слушаем сообщения от клиента (keep-alive)
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break
        
        update_task.cancel()
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
