#!/bin/bash

echo "📊 Проверка цен подарков"
echo ""

echo "1️⃣  LIMITED NFT в базе:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, model_name, backdrop_name FROM shop_gifts WHERE slug IS NOT NULL LIMIT 5;'"

echo ""
echo "2️⃣  Цены LIMITED NFT:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT title, ton_price, price, price_update FROM shop_gifts WHERE slug IS NOT NULL LIMIT 5;'"

echo ""
echo "3️⃣  Настройки:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db 'SELECT key, value FROM settings;'"

echo ""
echo "✅ Проверка завершена"
