#!/bin/bash
set -e

echo "🔧 Исправление импорта в shop.py..."

cd /Users/macbook/Documents/shell

# 1. Копируем исправленный auth.py
echo "📤 Копирование auth.py..."
scp server/app/routers/auth.py root@shelloch.xyz:/root/shell/server/app/routers/

# 2. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 3. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 3

# 4. Проверяем статус
echo "✓ Проверка статуса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

# 5. Проверяем логи
echo ""
echo "📋 Последние логи:"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 20 --no-pager | tail -10"

echo ""
echo "✅ Исправление завершено!"
