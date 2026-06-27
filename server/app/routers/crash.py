from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from app.crash_game import crash_game
from app.config import BOT_TOKEN, ADMIN_IDS
from app.utils.validate import validate_init_data
from app.utils.balance import get_user_balance
from app.utils.database import get_db_connection
from urllib.parse import parse_qs
import json
import sqlite3
import asyncio
import secrets
from typing import List
from app.utils.error_logger import send_error_log
from app.utils.limiter import limiter

router = APIRouter(prefix="/api/crash", tags=["crash"])

# Хранилище токенов для WebSocket аутентификации {token: user_id}
_ws_tokens: dict[str, int] = {}
_ws_tokens_by_user: dict[int, str] = {}


def _generate_ws_token(user_id: int) -> str:
    """Генерирует одноразовый токен для WebSocket подключения"""
    # Удаляем старый токен пользователя если есть
    if user_id in _ws_tokens_by_user:
        old_token = _ws_tokens_by_user[user_id]
        _ws_tokens.pop(old_token, None)
    token = secrets.token_hex(16)
    _ws_tokens[token] = user_id
    _ws_tokens_by_user[user_id] = token
    return token

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # Храним соединения по user_id: {user_id: websocket}
        self.active_connections: dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Подключает WebSocket и закрывает старые соединения этого пользователя"""
        # Если у этого user_id уже есть активное соединение - закрываем его
        if user_id in self.active_connections:
            old_ws = self.active_connections[user_id]
            try:
                await old_ws.close(code=1000, reason="New connection from same user")
                print(f"🔌 Закрыто старое соединение для user_id={user_id}")
            except Exception as e:
                print(f"⚠️ Ошибка закрытия старого соединения: {e}")
                await send_error_log(e, "crash.py: ConnectionManager.connect (close old)")
        
        # Принимаем новое соединение
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🔌 WebSocket подключен для user_id={user_id}. Всего уникальных: {len(self.active_connections)}")
    
    def disconnect(self, user_id: int):
        """Отключает WebSocket по user_id"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"🔌 WebSocket отключен для user_id={user_id}. Осталось: {len(self.active_connections)}")
    
    async def disconnect_all(self):
        """Отключает все WebSocket соединения (для graceful shutdown)"""
        print(f"🔌 Закрываю все WebSocket соединения ({len(self.active_connections)})...")
        for user_id, connection in list(self.active_connections.items()):
            try:
                await connection.close(code=1001, reason="Server restarting")
            except Exception as e:
                print(f"❌ Ошибка закрытия WebSocket для user_id={user_id}: {e}")
                await send_error_log(e, "crash.py: ConnectionManager.disconnect_all")
        self.active_connections.clear()
        print("✅ Все WebSocket соединения закрыты")
    
    async def broadcast(self, message: dict):
        """Отправка сообщения всем подключенным клиентам"""
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Ошибка отправки в WebSocket для user_id={user_id}: {e}")
                await send_error_log(e, "crash.py: ConnectionManager.broadcast")
                disconnected_users.append(user_id)
        
        # Удаляем отключенные соединения
        for user_id in disconnected_users:
            self.disconnect(user_id)

manager = ConnectionManager()

class BetRequest(BaseModel):
    initData: str
    amount: float

class CashoutRequest(BaseModel):
    initData: str

class CancelBetRequest(BaseModel):
    initData: str


@router.post("/cancel")
@limiter.limit("10/1minute")
async def cancel_bet(cancel_req: CancelBetRequest, request: Request):
    """Отменяет ставку до начала раунда"""
    is_valid = validate_init_data(cancel_req.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")

    try:
        parsed = parse_qs(cancel_req.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
    except Exception as e:
        await send_error_log(e, "crash.py: cancel_bet (user data)")
        raise HTTPException(status_code=403, detail="Invalid user data")

    result = crash_game.cancel_bet(user_id)

    if result["success"]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = int(round(current_balance + result["amount"]))
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
            conn.commit()
            conn.close()
            user_balance = get_user_balance(user_id)
            result.update(user_balance)
        except sqlite3.Error as e:
            await send_error_log(e, "crash.py: cancel_bet (db)")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return result


@router.get("/history")
@limiter.limit("3/5minute")
async def get_crash_history(request: Request):
    """Возвращает полную историю краш-игры"""
    return {
        "history": crash_game.history[-50:]
    }

@router.post("/bet")
@limiter.limit("100/35minute")
async def place_bet(bet: BetRequest, request: Request):
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
        username = user.get('first_name') or user.get('username', 'User')
        avatar = user.get('photo_url')
    except Exception as e:
        await send_error_log(e, "crash.py: place_bet (user data)")
        raise HTTPException(status_code=403, detail="Invalid user data")
    
    # Валидация: только целые числа и положительные значения
    amount = bet.amount
    
    # Проверка что amount - целое число (может прийти float из JSON)
    if not isinstance(amount, (int, float)) or amount != int(amount):
        raise HTTPException(status_code=400, detail="Сумма ставки должна быть целым числом")
    
    amount = int(amount)
    
    # Фильтрация отрицательных значений
    if amount < 0:
        raise HTTPException(status_code=400, detail="Сумма ставки не может быть отрицательной")
    
    # Минимальная ставка 25 звезд
    if amount < 25:
        raise HTTPException(status_code=400, detail="Минимальная ставка 25 звезд")
    
    # Максимальная ставка 20000 звезд
    if amount > 20000:
        raise HTTPException(status_code=400, detail="Максимальная ставка 20000 звезд")
    
    # Проверяем баланс
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[0] < amount:
            raise HTTPException(status_code=400, detail="Недостаточно средств")
        
        # Снимаем со счета
        new_balance = int(round(result[0] - amount))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()
        conn.close()
        
        # Размещаем ставку (используем валидированный amount)
        result = crash_game.place_bet(user_id, amount, username, avatar)
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        result.update(user_balance)
        
        return result
    except sqlite3.Error as e:
        await send_error_log(e, "crash.py: place_bet (db)")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/cashout")
@limiter.limit("100/25minute")
async def cashout(cashout_request: CashoutRequest, request: Request):
    """Забирает выигрыш"""
    # Проверяем initData
    is_valid = validate_init_data(cashout_request.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")
    
    # Извлекаем user_id из initData
    try:
        parsed = parse_qs(cashout_request.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user data")
    
    result = crash_game.cashout(user_id)
    
    if result["success"]:
        # Начисляем выигрыш
        try:
            conn = get_db_connection()
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
            await send_error_log(e, "crash.py: cashout (db)")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return result



class AuthTokenRequest(BaseModel):
    initData: str

class AuthTokenResponse(BaseModel):
    token: str


@router.post("/auth-token")
@limiter.limit("20/1minute")
async def get_ws_auth_token(req: AuthTokenRequest, request: Request):
    """Получить токен для WebSocket подключения к краш-игре"""
    is_valid = validate_init_data(req.initData, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid init data")

    try:
        parsed = parse_qs(req.initData)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(user_data)
        user_id = user.get('id')
    except Exception as e:
        await send_error_log(e, "crash.py: auth-token (user data)")
        raise HTTPException(status_code=403, detail="Invalid user data")

    token = _generate_ws_token(user_id)
    return {"token": token, "userId": user_id}


@router.websocket("/ws")
async def websocket_crash(websocket: WebSocket, token: str = None, initData: str = None):
    """WebSocket endpoint для краш игры.
    Аутентификация через query param token (предпочтительно) или initData (legacy).
    """
    user_id = None
    
    # Приоритет 1: токен
    if token and token in _ws_tokens:
        user_id = _ws_tokens.pop(token)  # одноразовый токен
        _ws_tokens_by_user.pop(user_id, None)
    
    # Приоритет 2: initData (legacy)
    if not user_id and initData:
        from app.routers.auth import verify_init_data
        user_data = verify_init_data(initData)
        if user_data:
            user_id = user_data.get('id')
    
    # Если не удалось получить user_id - используем анонимный ID
    if not user_id:
        user_id = id(websocket)
        print(f"⚠️ Анонимное подключение, используется ID: {user_id}")
    
    # Подключаем с user_id (закроет старые соединения этого пользователя)
    await manager.connect(websocket, user_id)
    
    try:
        # Отправляем начальное состояние с nextBet для этого пользователя
        initial_state = crash_game.get_state(user_id=user_id)
        await websocket.send_json(initial_state)
        
        # Фоновая задача для отправки обновлений
        async def send_updates():
            while True:
                try:
                    state = crash_game.get_state(user_id=user_id)
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
        await send_error_log(e, "crash.py: websocket_crash")
    finally:
        manager.disconnect(user_id)

@router.websocket("/admin/ws")
async def admin_websocket_endpoint(websocket: WebSocket, initData: str = None):
    """Скрытный WebSocket тоннель для админов - подключается только из админки"""
    await websocket.accept()
    
    try:
        # Получаем initData из query параметров
        if not initData:
            await websocket.close(code=1008, reason="Missing initData")
            return
        
        # Валидация
        is_valid = validate_init_data(initData, BOT_TOKEN)
        if not is_valid:
            await websocket.close(code=1008, reason="Invalid initData")
            return
        
        # Проверка что это админ
        parsed = parse_qs(initData)
        user_data = json.loads(parsed['user'][0])
        user_id = int(user_data['id'])
        
        if user_id not in ADMIN_IDS:
            await websocket.close(code=1008, reason="Forbidden")
            return
        
        print(f"🔐 Admin WebSocket tunnel connected: {user_id}")
        
        # Отправляем обновления каждые 100ms
        while True:
            game_state = crash_game.get_state()
            
            # Формируем минимальный ответ для админа (без списка ставок)
            admin_state = {
                "gameId": game_state["gameId"],
                "isRunning": game_state["isRunning"],
                "currentMultiplier": game_state.get("currentMultiplier", 1.0),
                "startTime": game_state.get("startTime"),
                "history": game_state["history"],
                "betsCount": len(game_state["bets"]),  # Только количество ставок
                "crashed": game_state.get("crashed", False),
                "crashedAt": game_state.get("crashedAt")
            }
            
            await websocket.send_json(admin_state)
            await asyncio.sleep(0.1)  # 100ms для плавности
            
    except WebSocketDisconnect:
        print(f"🔐 Admin WebSocket tunnel disconnected: {user_id}")
    except Exception as e:
        print(f"Admin WebSocket error: {e}")
        await send_error_log(e, "crash.py: admin_websocket_endpoint")
        try:
            await websocket.close()
        except:
            pass
