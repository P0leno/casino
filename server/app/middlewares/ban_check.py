"""
Middleware для проверки бана пользователя
"""

from fastapi import HTTPException, Request
import sqlite3
from app.config import DB_PATH
from app.routers.auth import parse_init_data

def check_user_ban(init_data: str):
    """
    Проверка бана пользователя по initData
    Возвращает user_id если не забанен
    Выбрасывает HTTPException если забанен
    """
    user_data = parse_init_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid initData")
    
    user_id = user_data.get('id')
    
    # Проверяем бан в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        raise HTTPException(status_code=403, detail="User is banned")
    
    return user_id

async def ban_check_middleware(request: Request, call_next):
    """
    Middleware для проверки бана на всех запросах кроме /api/check-ban и /api/validate
    """
    # Разрешенные пути (не проверяем бан)
    allowed_paths = ['/api/check-ban', '/api/validate', '/api/health', '/']
    
    if request.url.path in allowed_paths or not request.url.path.startswith('/api/'):
        return await call_next(request)
    
    # Пытаемся получить initData из body
    try:
        body = await request.body()
        if body:
            import json
            try:
                data = json.loads(body.decode())
                init_data = data.get('initData')
                
                if init_data:
                    # Проверяем бан
                    user_data = parse_init_data(init_data)
                    if user_data:
                        user_id = user_data.get('id')
                        
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
                        result = cursor.fetchone()
                        conn.close()
                        
                        if result and result[0]:
                            return HTTPException(status_code=403, detail="User is banned").__call__(request.scope, request.receive, request.send)
            except:
                pass
    except:
        pass
    
    # Восстанавливаем body для дальнейшей обработки
    async def receive():
        return {"type": "http.request", "body": body}
    
    request._receive = receive
    
    return await call_next(request)
