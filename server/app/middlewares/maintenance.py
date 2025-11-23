"""
Middleware для режима технических работ
Блокирует доступ не-админам когда maintenance_mode включен
"""

from fastapi import Request
from fastapi.responses import JSONResponse
import sqlite3
from app.config import DB_PATH, ADMIN_IDS
from app.routers.auth import verify_init_data

def is_maintenance_mode() -> bool:
    """Проверить включен ли режим технических работ"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == '1':
            return True
        return False
    except Exception as e:
        print(f"Error checking maintenance mode: {e}")
        return False

async def maintenance_middleware(request: Request, call_next):
    """
    Middleware для проверки режима технических работ
    Пропускает админов, блокирует остальных
    """
    # Разрешенные пути (не проверяем режим)
    allowed_paths = [
        '/api/validate',
        '/api/check-admin',
        '/api/check-maintenance',
        '/api/check-ban',
        '/api/health',
        '/'
    ]
    
    # Если путь разрешен или не API - пропускаем
    if request.url.path in allowed_paths or not request.url.path.startswith('/api/'):
        return await call_next(request)
    
    # Проверяем режим технических работ
    if not is_maintenance_mode():
        return await call_next(request)
    
    # Режим тех. работ включен - проверяем админа
    body = await request.body()
    
    if body:
        try:
            import json
            from urllib.parse import parse_qs
            
            data = json.loads(body.decode())
            init_data = data.get('initData')
            
            if init_data:
                # Парсим initData для получения user_id
                try:
                    parsed = parse_qs(init_data)
                    user_data_str = parsed.get('user', [''])[0]
                    
                    if user_data_str:
                        user_obj = json.loads(user_data_str)
                        user_id = user_obj.get('id')
                        
                        # Проверяем что это админ
                        if user_id and user_id in ADMIN_IDS:
                            # Админ - пропускаем
                            print(f"[MAINTENANCE] Admin {user_id} allowed during maintenance")
                            
                            # Восстанавливаем body для следующих обработчиков
                            async def receive():
                                return {"type": "http.request", "body": body}
                            
                            request._receive = receive
                            return await call_next(request)
                        else:
                            # Не админ - блокируем
                            print(f"[MAINTENANCE] User {user_id} blocked during maintenance")
                            return JSONResponse(
                                status_code=503,
                                content={
                                    "detail": "Технические работы",
                                    "message": "Ведутся технические работы. Попробуйте позже.",
                                    "maintenance": True
                                }
                            )
                except Exception as parse_error:
                    print(f"[MAINTENANCE] Parse error: {parse_error}")
                    # Не смогли распарсить - блокируем
                    pass
        except Exception as e:
            print(f"Maintenance middleware error: {e}")
    
    # По умолчанию блокируем если режим тех. работ
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Технические работы",
            "message": "Ведутся технические работы. Попробуйте позже.",
            "maintenance": True
        }
    )
