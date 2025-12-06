# 🚀 ФИНАЛЬНЫЙ ДЕПЛОЙ WEBSOCKET С АВТОРИЗАЦИЕЙ

## ✅ Что изменено:

### Frontend (Crash.jsx)
```javascript
// Добавлен initData в WebSocket URL
const initData = window.Telegram?.WebApp?.initData || ''
const wsUrlWithAuth = `${wsUrl}/api/crash/ws?initData=${encodeURIComponent(initData)}`
const ws = new WebSocket(wsUrlWithAuth)
```

### Backend (maintenance.py)
```python
# Проверка авторизации для WebSocket через query параметры
if '/ws' in request.url.path:
    query_params = dict(request.query_params)
    init_data = query_params.get('initData')
    # Проверяем что user_id в ADMIN_IDS
```

### Backend (crash.py)
```python
@router.websocket("/ws")
async def websocket_crash(websocket: WebSocket, initData: str = None):
    # initData передается как query параметр
```

## 📦 ДЕПЛОЙ НА СЕРВЕР:

### Шаг 1: Обновить Backend

```bash
# На сервере
cd ~/shelloch/server

# Обновить maintenance.py
nano app/middlewares/maintenance.py
```

**Найди строки (~54-57):**
```python
# Если путь разрешен или не API - пропускаем
if request.url.path in allowed_paths or not request.url.path.startswith('/api/'):
    return await call_next(request)

# Проверяем режим технических работ
maintenance_enabled = is_maintenance_mode()
```

**Вставь ПЕРЕД "# Проверяем режим технических работ":**
```python
# Если путь разрешен или не API - пропускаем
if request.url.path in allowed_paths or not request.url.path.startswith('/api/'):
    return await call_next(request)

# Для WebSocket запросов проверяем initData в query параметрах
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
                
                if user_id in ADMIN_IDS:
                    print(f"[MAINTENANCE] ✅ WebSocket: ADMIN {user_id} allowed")
                    return await call_next(request)
        except Exception as e:
            print(f"[MAINTENANCE] ❌ WebSocket auth error: {e}")
    
    # WebSocket без валидной авторизации - блокируем
    print(f"[MAINTENANCE] ❌ WebSocket blocked: no valid auth")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Технические работы",
            "maintenance": True
        }
    )

# Проверяем режим технических работ
maintenance_enabled = is_maintenance_mode()
```

**Обновить crash.py:**
```bash
nano app/routers/crash.py
```

Найди строку:
```python
async def websocket_crash(websocket: WebSocket):
```

Замени на:
```python
async def websocket_crash(websocket: WebSocket, initData: str = None):
    """WebSocket endpoint для краш игры"""
    # initData передается как query параметр для авторизации
```

**Сохрани и перезапусти:**
```bash
sudo systemctl restart shelloch-backend
sudo journalctl -u shelloch-backend -f
```

### Шаг 2: Обновить Frontend

**Вариант A - через SCP с локальной машины:**
```bash
# На локальной машине
cd /Users/macbook/Documents/shell
scp frontend-with-auth.tar.gz root@wonderfulhot.aeza.network:/tmp/
```

**На сервере:**
```bash
cd /tmp
sudo tar -xzf frontend-with-auth.tar.gz -C /var/www/shelloch/
sudo chown -R www-data:www-data /var/www/shelloch/
rm frontend-with-auth.tar.gz
```

**Вариант B - пересобрать на сервере:**
```bash
cd ~/shelloch/client
git pull origin main
npm run build
sudo cp -r dist/* /var/www/shelloch/
```

### Шаг 3: Проверка

**На сервере смотреть логи:**
```bash
sudo journalctl -u shelloch-backend -f
```

**В браузере:**
1. Очисти кэш: `Ctrl+Shift+R`
2. Открой консоль (F12)

**Ожидаемые логи на сервере:**
```
[MAINTENANCE] ✅ WebSocket: ADMIN 1056148947 allowed
🔌 WebSocket подключен. Всего: 1
```

**В консоли браузера:**
```
🔌 WebSocket connected to crash game
```

## ✅ Результат:

**До:**
- ❌ WebSocket: 503 Service Unavailable
- ❌ Спам запросов /api/crash/state каждые 200ms
- ❌ Maintenance блокирует всё

**После:**
- ✅ WebSocket работает с авторизацией
- ✅ Polling отключается
- ✅ Админы работают при включенном maintenance
- ✅ Обычные пользователи блокируются (если maintenance включен)

## 🔍 Отладка:

### WebSocket не подключается:
```bash
# Проверь что initData передается
grep "api/crash/ws?initData" /var/www/shelloch/assets/index-*.js

# Проверь middleware
grep "WebSocket: ADMIN" ~/shelloch/server/app/middlewares/maintenance.py
```

### Всё ещё 503:
```bash
# Проверь что middleware обновлен
grep "if '/ws' in request.url.path:" ~/shelloch/server/app/middlewares/maintenance.py

# Проверь что бэкенд перезапущен
sudo systemctl status shelloch-backend
```

### Polling не останавливается:
- Значит WebSocket не подключился
- Смотри логи бэкенда
- Проверь что фронтенд обновлен

## 📊 Коммиты:

```
4f2844f WebSocket авторизация через initData
2913a24 Разрешить WebSocket подключения в maintenance
fca96dc Исправлен WebSocket URL
4736f7b Добавлен WebSocket endpoint
```

## 🎯 Для обычных пользователей:

Если хочешь чтобы краш-игра работала для всех (не только админов):

```bash
# Отключи maintenance
sqlite3 ~/shelloch/server/users.db "UPDATE settings SET value='0' WHERE key='maintenance_mode';"
sudo systemctl restart shelloch-backend
```

Или добавь в `allowed_paths`:
```python
'/api/crash/state',
'/api/crash/bet',
'/api/crash/cashout',
'/api/crash/cancel',
```
