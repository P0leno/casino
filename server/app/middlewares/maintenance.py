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
    Пропускает всех у кого user_id есть в ADMIN_IDS из .env
    Блокирует остальных при включенном maintenance_mode
    """
    # ВАЖНО: Всегда пропускаем OPTIONS запросы для CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Разрешенные пути (не проверяем maintenance для этих путей)
    allowed_paths = [
        '/api/validate',
        '/api/check-admin',
        '/api/check-maintenance',
        '/api/check-ban',
        '/api/check-user-maintenance',
        '/api/get-maintenance',
        '/api/toggle-maintenance',
        '/api/health',
        '/api/crash/ws',  # WebSocket для краш игры
        '/'
    ]
    
    # Если путь разрешен или не API - пропускаем
    # Также пропускаем все WebSocket запросы (любые /ws пути)
    if (request.url.path in allowed_paths or 
        not request.url.path.startswith('/api/') or 
        '/ws' in request.url.path):
        return await call_next(request)
    
    # Проверяем режим технических работ
    maintenance_enabled = is_maintenance_mode()
    
    if not maintenance_enabled:
        # Режим выключен - всем доступ
        return await call_next(request)
    
    # Режим тех. работ ВКЛЮЧЕН - проверяем является ли пользователь админом
    print(f"[MAINTENANCE] Mode enabled, checking user for path: {request.url.path}")
    print(f"[MAINTENANCE] ADMIN_IDS from config: {ADMIN_IDS}")
    
    body = await request.body()
    
    # Восстанавливаем body для следующих обработчиков
    async def receive():
        return {"type": "http.request", "body": body}
    
    request._receive = receive
    
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
                        
                        print(f"[MAINTENANCE] Parsed user_id: {user_id} (type: {type(user_id)})")
                        
                        # Проверяем что user_id есть в ADMIN_IDS
                        if user_id:
                            user_id_int = int(user_id)
                            is_admin = user_id_int in ADMIN_IDS
                            
                            print(f"[MAINTENANCE] Check: {user_id_int} in {ADMIN_IDS} = {is_admin}")
                            
                            if is_admin:
                                # Админ - даем полный доступ ко всем API
                                print(f"[MAINTENANCE] ✅ ADMIN {user_id_int} allowed full access")
                                return await call_next(request)
                            else:
                                # Не админ - блокируем
                                print(f"[MAINTENANCE] ❌ USER {user_id_int} blocked (not in ADMIN_IDS)")
                                return JSONResponse(
                                    status_code=503,
                                    content={
                                        "detail": "Технические работы",
                                        "message": "Ведутся технические работы. Попробуйте позже.",
                                        "maintenance": True
                                    }
                                )
                except Exception as parse_error:
                    print(f"[MAINTENANCE] ❌ Parse error: {parse_error}")
                    import traceback
                    traceback.print_exc()
                    # Не смогли распарсить - блокируем
        except Exception as e:
            print(f"[MAINTENANCE] ❌ Middleware error: {e}")
            import traceback
            traceback.print_exc()
    
    # По умолчанию блокируем если режим тех. работ и не смогли определить админа
    print(f"[MAINTENANCE] ❌ Default block (no valid initData or user_id)")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Технические работы",
            "message": "Ведутся технические работы. Попробуйте позже.",
            "maintenance": True
        }
    )
