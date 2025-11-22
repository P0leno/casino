#!/bin/bash

echo "=== Проверка парсера цен ==="
echo ""

echo "1️⃣  Проверяем установлен ли curl_cffi..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'import curl_cffi; print(\"✅ curl_cffi установлен\")' 2>&1"

echo ""
echo "2️⃣  Проверяем текущие цены в БД..."
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, model_name, price, price_update FROM shop_gifts LIMIT 5;'"

echo ""
echo "3️⃣  Проверяем что парсер запустился (логи)..."
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 50 --no-pager | grep -i 'price.*updater'"

echo ""
echo "4️⃣  Запускаем парсер вручную для теста..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'import asyncio; from app.tasks.price_updater import update_all_prices; asyncio.run(update_all_prices())'"

echo ""
echo "5️⃣  Проверяем цены после обновления..."
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, model_name, price, price_update FROM shop_gifts LIMIT 5;'"
