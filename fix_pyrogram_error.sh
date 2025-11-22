#!/bin/bash
set -e

echo "🔧 Исправление ошибки Pyrogram..."

cd /Users/macbook/Documents/shell

# Копируем исправленный gift_parser.py
echo "📤 Копирование gift_parser.py..."
scp server/app/tasks/gift_parser.py root@shelloch.xyz:/opt/shell/app/tasks/

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
echo "Изменения:"
echo "  ✓ Добавлен no_updates=True для Pyrogram"
echo "  ✓ Безопасное закрытие клиента"
echo "  ✓ Дополнительный traceback для отладки"
