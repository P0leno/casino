#!/bin/bash
set -e

echo "🔧 Исправление парсера цен..."

cd /Users/macbook/Documents/shell

# 1. Копируем исправленный парсер
echo "📤 Копирование price_updater.py..."
scp server/app/tasks/price_updater.py root@shelloch.xyz:/root/shell/server/app/tasks/

# 2. Проверяем LIMITED NFT в БД
echo ""
echo "📦 LIMITED NFT в базе:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db \"SELECT title, model_name, backdrop_name, slug FROM shop_gifts WHERE slug IS NOT NULL LIMIT 5;\""

# 3. Запускаем парсер вручную для теста
echo ""
echo "🔄 Запуск парсера цен..."
ssh root@shelloch.xyz "cd /root/shell/server && timeout 120 venv/bin/python app/tasks/price_updater.py 2>&1 | head -100"

# 4. Проверяем обновленные цены
echo ""
echo "💰 Обновленные цены:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db \"SELECT title, price, price_update FROM shop_gifts WHERE slug IS NOT NULL;\""

# 5. Перезапускаем бэкенд
echo ""
echo "🔄 Перезапуск бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

echo ""
echo "✅ Готово! Парсер теперь работает с LIMITED NFT (по slug)"
