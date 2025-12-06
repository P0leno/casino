"""
Middleware для проверки бана пользователя
"""

from fastapi import Request
from fastapi.responses import JSONResponse
import sqlite3
from app.config import DB_PATH
from app.routers.auth import verify_init_data

async def ban_check_middleware(request: Request, call_next):
    """
    Middleware для проверки бана на всех API запросах кроме check-ban, validate и health
    """
    # Пропускаем WebSocket запросы (они не имеют body с initData)
    if request.url.path.endswith('/ws') or 'websocket' in request.headers.get('upgrade', '').lower():
        return await call_next(request)
    
    # Разрешенные пути (не проверяем бан)
    allowed_paths = ['/api/check-ban', '/api/validate', '/api/health', '/']
    
    # Если путь разрешен или не API - пропускаем
    if request.url.path in allowed_paths or not request.url.path.startswith('/api/'):
        return await call_next(request)
    
    # Читаем body
    body = await request.body()
    
    # Пытаемся получить initData
    if body:
        try:
            import json
            data = json.loads(body.decode())
            init_data = data.get('initData')
            
            if init_data:
                # Проверяем валидность
                user_data = verify_init_data(init_data)
                
                if user_data:
                    user_id = user_data.get('telegram_id')
                    
                    # Проверяем бан в БД
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    # Если забанен - возвращаем 403
                    if result and result[0] == 1:
                        print(f"[BAN MIDDLEWARE] User {user_id} is BANNED, blocking {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "User is banned"}
                        )
                    else:
                        print(f"[BAN MIDDLEWARE] User {user_id} is NOT banned, allowing {request.url.path}")
        except Exception as e:
            print(f"Ban check middleware error: {e}")
            pass
    
    # Восстанавливаем body для следующих обработчиков
    async def receive():
        return {"type": "http.request", "body": body}
    
    request._receive = receive
    
    return await call_next(request)
