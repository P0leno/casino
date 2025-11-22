#!/bin/bash
set -e

echo "🚀 Деплой промокодов..."

cd /Users/macbook/Documents/shell

# 1. Копируем серверные файлы
echo "📤 Копирование серверных файлов..."
scp server/app/database/db.py root@shelloch.xyz:/root/shell/server/app/database/
scp server/app/routers/auth.py root@shelloch.xyz:/root/shell/server/app/routers/
scp server/app/routers/promocode.py root@shelloch.xyz:/root/shell/server/app/routers/

# 2. Копируем клиентские файлы
echo "📤 Копирование клиентских файлов..."
scp client/src/components/PromoCodeModal.jsx root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/PromoCodeModal.css root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/Settings.jsx root@shelloch.xyz:/root/shell/client/src/components/

# 3. Обновляем структуру БД (добавит avatar_url и promo_history)
echo "🔧 Обновление структуры БД..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'from app.database.db import init_db; init_db()'"

# 4. Билд клиента
echo "🔨 Билд клиента..."
ssh root@shelloch.xyz "cd /root/shell/client && npm run build"

# 5. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 6. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 5

# 7. Проверяем статус
echo "✓ Статус сервиса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend" && echo "✅ Сервис запущен" || echo "❌ Сервис не запущен"

# 8. Проверяем логи
echo "📋 Последние логи:"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 30 --no-pager"

echo ""
echo "✅ Деплой завершен!"
