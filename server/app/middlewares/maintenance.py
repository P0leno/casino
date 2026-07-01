"""
Middleware для режима технических работ
Блокирует доступ не-админам когда maintenance_mode включен
"""

from fastapi import Request
from fastapi.responses import JSONResponse

def is_maintenance_mode() -> bool:
    """Проверить включен ли режим технических работ (из Redis с fallback на SQLite)"""
    try:
        from app.utils.redis_models import RedisSettings
        setting = RedisSettings.get('maintenance_mode')

        if setting and setting['value'] == '1':
            return True
        return False
    except Exception as e:
        print(f"Error checking maintenance mode: {e}")
        return False

async def maintenance_middleware(request: Request, call_next):
    """
    Middleware для проверки режима технических работ
    Пропускает админов (проверка через RedisSettings.is_admin)
    Блокирует остальных при включенном maintenance_mode
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    allowed_paths = [
        '/api/validate',
        '/api/check-admin',
        '/api/check-maintenance',
        '/api/check-ban',
        '/api/check-user-maintenance',
        '/api/get-maintenance',
        '/api/toggle-maintenance',
        '/api/health',
        '/'
    ]

    if (request.url.path in allowed_paths or
        not request.url.path.startswith('/api/') or
        request.url.path.startswith('/api/crash/')):
        return await call_next(request)

    if '/ws' in request.url.path:
        query_params = dict(request.query_params)
        init_data = query_params.get('initData')

        if init_data:
            try:
                from urllib.parse import parse_qs
                import json

                parsed = parse_qs(init_data)
                user_data_str = parsed.get('user', [''])[0]

                if user_data_str:
                    user_obj = json.loads(user_data_str)
                    user_id = int(user_obj.get('id'))

                    from app.utils.redis_models import RedisSettings
                    if user_id and RedisSettings.is_admin(int(user_id)):
                        print(f"[MAINTENANCE] ✅ WebSocket: ADMIN {user_id} allowed")
                        return await call_next(request)
            except Exception as e:
                print(f"[MAINTENANCE] ❌ WebSocket auth error: {e}")

        print(f"[MAINTENANCE] ❌ WebSocket blocked: no valid auth")
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Технические работы",
                "maintenance": True
            }
        )

    maintenance_enabled = is_maintenance_mode()

    if not maintenance_enabled:
        return await call_next(request)

    print(f"[MAINTENANCE] Mode enabled, checking user for path: {request.url.path}")

    body = await request.body()

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
                try:
                    parsed = parse_qs(init_data)
                    user_data_str = parsed.get('user', [''])[0]

                    if user_data_str:
                        user_obj = json.loads(user_data_str)
                        user_id = user_obj.get('id')

                        if user_id:
                            user_id_int = int(user_id)

                            from app.utils.redis_models import RedisSettings
                            is_admin = RedisSettings.is_admin(user_id_int)

                            print(f"[MAINTENANCE] Check: {user_id_int} is_admin = {is_admin}")

                            if is_admin:
                                print(f"[MAINTENANCE] ✅ ADMIN {user_id_int} allowed full access")
                                return await call_next(request)
                            else:
                                print(f"[MAINTENANCE] ❌ USER {user_id_int} blocked")
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
        except Exception as e:
            print(f"[MAINTENANCE] ❌ Middleware error: {e}")
            import traceback
            traceback.print_exc()

    print(f"[MAINTENANCE] ❌ Default block (no valid initData or user_id)")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Технические работы",
            "message": "Ведутся технические работы. Попробуйте позже.",
            "maintenance": True
        }
    )
