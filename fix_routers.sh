#!/bin/bash
set -e

echo "🔧 Восстановление всех роутеров..."

cd /Users/macbook/Documents/shell

# Копируем ВСЕ роутеры на сервер
echo "📤 Копирование всех роутеров..."
scp server/app/routers/*.py root@shelloch.xyz:/root/shell/server/app/routers/

# Проверяем что все файлы скопированы
echo ""
echo "✓ Проверка файлов на сервере:"
ssh root@shelloch.xyz "ls -la /root/shell/server/app/routers/*.py"

# Рестарт бэкенда
echo ""
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 3

# Проверяем статус
echo ""
echo "✓ Проверка статуса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend" && echo "✅ Сервис запущен" || echo "❌ Сервис не запустился"

# Проверяем логи
echo ""
echo "📋 Последние логи:"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 30 --no-pager | tail -20"

echo ""
echo "✅ Восстановление завершено!"
