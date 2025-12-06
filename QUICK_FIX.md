# 🚨 БЫСТРОЕ ИСПРАВЛЕНИЕ WEBSOCKET 404

## Проблема:
- Фронтенд: пытается `/ws/crash` (старый билд)
- Бэкенд: endpoint на `/api/crash/ws` (новый код локально, старый на сервере)

## ✅ Решение (на сервере):

### Шаг 1: Обновить файл crash.py

Скопируй с локальной машины или отредактируй прямо на сервере:

```bash
# На сервере
cd ~/shelloch/server  # или твой путь
nano app/routers/crash.py
```

Добавь в начало файла (после импортов):
```python
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from typing import List

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
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Ошибка отправки в WebSocket: {e}")
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
```

В конец файла добавь:
```python
@router.websocket("/ws")
async def websocket_crash(websocket: WebSocket):
    """WebSocket endpoint для краш игры"""
    await manager.connect(websocket)
    
    try:
        initial_state = crash_game.get_state()
        await websocket.send_json(initial_state)
        
        async def send_updates():
            while True:
                try:
                    state = crash_game.get_state()
                    await websocket.send_json(state)
                    await asyncio.sleep(0.05)
                except Exception:
                    break
        
        update_task = asyncio.create_task(send_updates())
        
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
```

### Шаг 2: Перезапустить бэкенд

```bash
sudo systemctl restart shelloch-backend
sudo journalctl -u shelloch-backend -f
```

### Шаг 3: Обновить фронтенд

Вариант A - скопировать с локальной машины:
```bash
# На локальной машине
cd /Users/macbook/Documents/shell/client
rsync -avz dist/ root@wonderfulhot.aeza.network:/var/www/shelloch/
```

Вариант B - пересобрать на сервере:
```bash
# На сервере
cd ~/shelloch/client
npm run build
sudo cp -r dist/* /var/www/shelloch/
```

Вариант C - только обновить JS файл:
```bash
# На локальной машине - найти новый bundle
cd /Users/macbook/Documents/shell/client/dist/assets
# Загрузить index-Blck0evM.js на сервер
scp index-Blck0evM.js root@wonderfulhot.aeza.network:/var/www/shelloch/assets/
```

### Шаг 4: Проверка

1. Очисти кэш браузера: `Ctrl+Shift+R`
2. Консоль браузера: должно быть `🔌 WebSocket connected`
3. Логи сервера: должно быть `🔌 WebSocket подключен. Всего: 1`

## 📊 Ожидаемый результат:

**До:**
```
INFO: GET /ws/crash HTTP/1.1 404 Not Found
```

**После:**
```
🔌 WebSocket подключен. Всего: 1
```
