#!/bin/bash

echo "🧪 Тест системы цен"
echo ""

echo "1️⃣  Проверяем структуру БД..."
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'PRAGMA table_info(shop_gifts);' | grep -E '(ton_price|price_update)'"

echo ""
echo "2️⃣  Текущие данные в БД:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, ton_price, price FROM shop_gifts WHERE slug IS NOT NULL LIMIT 3;'"

echo ""
echo "3️⃣  Тест: обновление цены TON..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'import asyncio; from app.tasks.ton_price_updater import update_ton_price; asyncio.run(update_ton_price())'"

echo ""
echo "4️⃣  Тест: пересчет цен подарков..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'import asyncio; from app.tasks.ton_price_updater import recalculate_gift_prices; asyncio.run(recalculate_gift_prices())'"

echo ""
echo "5️⃣  Проверяем цены после пересчета:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, ton_price, price FROM shop_gifts WHERE slug IS NOT NULL LIMIT 3;'"

echo ""
echo "✅ Тест завершен!"
