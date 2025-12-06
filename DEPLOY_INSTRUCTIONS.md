# Инструкция по деплою краш игры с WebSocket

## ✅ Что готово локально:

1. **Backend:**
   - WebSocket endpoint `/api/crash/ws` создан ✅
   - ConnectionManager для управления подключениями ✅
   - 20 FPS обновления ✅

2. **Frontend:**
   - WebSocket подключение с fallback на polling ✅
   - URL изменен на `/api/crash/ws` ✅
   - **Билд создан** (1.28s) ✅

## 📦 Шаги деплоя:

### 1. Backend (на сервере через SSH)

```bash
# Подключиться к серверу
ssh user@wonderfulhot.aeza.network

# Перейти в директорию сервера
cd /path/to/shelloch/server

# Запушить изменения с локальной машины (сначала)
# На локальной машине:
cd /Users/macbook/Documents/shell
git push origin main

# Затем на сервере:
git pull origin main

# Перезапустить бэкенд
sudo systemctl restart shelloch-backend

# Проверить что запустилось
sudo systemctl status shelloch-backend

# Смотреть логи
sudo journalctl -u shelloch-backend -f
# Ожидаем: "🔌 WebSocket подключен. Всего: X"
```

### 2. Frontend (загрузить dist/)

**Вариант A: через SCP/SFTP**
```bash
# С локальной машины
cd /Users/macbook/Documents/shell/client
scp -r dist/* user@wonderfulhot.aeza.network:/path/to/nginx/html/
```

**Вариант B: через Git (если настроено)**
```bash
# На локальной машине (коммитить dist не рекомендуется)
# Вместо этого: билдить на сервере

# На сервере:
cd /path/to/shelloch/client
git pull origin main
npm run build
# Скопировать dist/ в nginx директорию
sudo cp -r dist/* /var/www/shelloch/
```

**Вариант C: через rsync (рекомендуется)**
```bash
# С локальной машины
cd /Users/macbook/Documents/shell/client
rsync -avz --delete dist/ user@wonderfulhot.aeza.network:/var/www/shelloch/
```

### 3. Проверить Nginx конфигурацию

Убедиться что WebSocket проксируется:

```nginx
location /api/crash/ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400;
}
```

Если нужно добавить - отредактировать конфиг:
```bash
sudo nano /etc/nginx/sites-available/shelloch
sudo nginx -t  # Проверить синтаксис
sudo systemctl reload nginx
```

## 🔍 Проверка после деплоя:

### Backend логи должны показывать:
```
🔌 WebSocket подключен. Всего: 1
INFO: 162.158.103.210:0 - "Upgrade /api/crash/ws HTTP/1.1" 101 Switching Protocols
```

### Браузер консоль должна показывать:
```javascript
🔌 WebSocket connected to crash game
```

### Если видите 404:
```
GET /ws/crash HTTP/1.1 404 Not Found
```
Значит фронтенд не обновлен - повторить шаг 2.

### Если видите ошибку соединения:
```
WebSocket connection to 'wss://...' failed
```
- Проверить nginx конфиг (шаг 3)
- Проверить что бэкенд запущен
- Проверить логи бэкенда

## 📊 Текущие коммиты для деплоя:

```
fca96dc Исправлен WebSocket URL: /api/crash/ws
4736f7b Добавлен WebSocket endpoint на бэкенде
f692dff Fallback на polling если WebSocket недоступен
e598c89 Улучшения краш игры: динамическая анимация, ракета
```

## 🚨 Откат в случае проблем:

### Backend:
```bash
cd /path/to/shelloch/server
git checkout HEAD~4  # Откатить на 4 коммита назад
sudo systemctl restart shelloch-backend
```

### Frontend:
```bash
# Загрузить старый билд из бэкапа
# или пересобрать с другой ветки
```

## ⚙️ Полезные команды:

```bash
# Проверить процессы
ps aux | grep python
ps aux | grep nginx

# Проверить порты
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :80

# Проверить WebSocket подключения
sudo netstat -an | grep ESTABLISHED | grep :8000

# Логи nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Логи бэкенда
sudo journalctl -u shelloch-backend -f -n 100
```

## 📁 Пути на сервере (примерные):

- Backend: `/home/user/shelloch/server/`
- Frontend HTML: `/var/www/shelloch/`
- Nginx config: `/etc/nginx/sites-available/shelloch`
- Systemd service: `/etc/systemd/system/shelloch-backend.service`

Уточни эти пути у админа сервера!
