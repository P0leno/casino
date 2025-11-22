#!/bin/bash

echo "🔍 Проверка shop.py на сервере..."
echo ""

echo "1️⃣  Проверка префикса router:"
ssh root@shelloch.xyz "grep 'router = APIRouter' /root/shell/server/app/routers/shop.py"

echo ""
echo "2️⃣  Проверка эндпоинтов:"
ssh root@shelloch.xyz "grep '@router' /root/shell/server/app/routers/shop.py | head -5"

echo ""
echo "3️⃣  Проверка импорта в run.py:"
ssh root@shelloch.xyz "grep 'from app.routers import' /root/shell/server/app/run.py"

echo ""
echo "4️⃣  Проверка регистрации router:"
ssh root@shelloch.xyz "grep 'shop.router' /root/shell/server/app/run.py"

echo ""
echo "5️⃣  Статус бэкенда:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

echo ""
echo "6️⃣  Последние логи (ошибки):"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 50 --no-pager | grep -i 'error\|traceback\|import' | tail -10"

echo ""
echo "7️⃣  Проверка что файл обновлен:"
ssh root@shelloch.xyz "stat /root/shell/server/app/routers/shop.py | grep Modify"
