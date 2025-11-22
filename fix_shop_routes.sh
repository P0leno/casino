#!/bin/bash
set -e

echo "🔧 Исправление роутов shop.py..."

cd /Users/macbook/Documents/shell

# Копируем исправленный shop.py
echo "📤 Копирование shop.py..."
scp server/app/routers/shop.py root@shelloch.xyz:/root/shell/server/app/routers/

# Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 3

# Проверяем статус
echo ""
echo "✓ Проверка статуса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

echo ""
echo "✅ Исправление завершено!"
echo ""
echo "Эндпоинты shop теперь:"
echo "  GET  /api/shop/gifts"
echo "  GET  /api/shop/gift/{gift_id}"
echo "  POST /api/shop/buy-gift"
