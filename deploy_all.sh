#!/bin/bash
set -e

echo "🚀 Полный деплой системы..."

cd /Users/macbook/Documents/shell

# 1. Копируем все файлы
echo "📤 Копирование файлов..."
scp server/app/database/db.py root@shelloch.xyz:/root/shell/server/app/database/
scp server/app/crash_game.py root@shelloch.xyz:/root/shell/server/app/
scp server/app/run.py root@shelloch.xyz:/root/shell/server/app/
scp server/app/tasks/gift_parser.py root@shelloch.xyz:/root/shell/server/app/tasks/
scp server/app/tasks/price_updater.py root@shelloch.xyz:/root/shell/server/app/tasks/
scp server/app/routers/auth.py root@shelloch.xyz:/root/shell/server/app/routers/
scp server/app/routers/admin.py root@shelloch.xyz:/root/shell/server/app/routers/
scp server/app/routers/payments.py root@shelloch.xyz:/root/shell/server/app/routers/
scp server/app/routers/game.py root@shelloch.xyz:/root/shell/server/app/routers/
scp client/src/components/Settings.jsx root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/Settings.css root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/Profile.jsx root@shelloch.xyz:/root/shell/client/src/components/

# 2. Пересоздаем БД структуру (добавит price_update колонку и таблицу settings)
echo "🔧 Обновление структуры БД..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'from app.database.db import init_db; init_db()'"

# 3. Проверяем что таблица settings и колонка price_update созданы
echo "✓ Проверка БД..."
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT key, value FROM settings;'" || echo "Settings OK"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'PRAGMA table_info(shop_gifts);' | grep price_update" || echo "price_update OK"

# 4. Устанавливаем curl_cffi если нет
echo "📦 Проверка зависимостей..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/pip install curl_cffi || echo 'curl_cffi уже установлен'"

# 5. Билд клиента
echo "🔨 Билд клиента..."
ssh root@shelloch.xyz "cd /root/shell/client && npm run build"

# 6. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 7. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 5

# 8. Проверяем статус
echo "✓ Статус сервиса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

# 9. Проверяем логи
echo "📋 Последние логи:"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 20 --no-pager | grep -E '(settings|price.*updater|Запущен)'"

echo ""
echo "✅ Деплой завершен!"
echo "🔗 Проверьте:"
echo "   - Админка: https://shelloch.xyz"
echo "   - Настройки: кнопка Переключатели"
echo "   - Парсер цен запущен (обновление каждый час)"
