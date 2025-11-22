#!/bin/bash
set -e

echo "🚀 Деплой финальных улучшений..."

cd /Users/macbook/Documents/shell

# 1. Копируем обновленные файлы клиента
echo "📤 Копирование файлов клиента..."
scp client/src/components/GiftDetailsModal.css root@shelloch.xyz:/opt/shell/client/src/components/
scp client/src/components/Settings.jsx root@shelloch.xyz:/opt/shell/client/src/components/
scp client/src/components/Settings.css root@shelloch.xyz:/opt/shell/client/src/components/
scp client/src/components/Profile.jsx root@shelloch.xyz:/opt/shell/client/src/components/
scp client/src/components/TabBar.css root@shelloch.xyz:/opt/shell/client/src/components/

# 2. Копируем обновленные файлы сервера
echo "📤 Копирование файлов сервера..."
scp server/app/database/db.py root@shelloch.xyz:/opt/shell/app/database/
scp server/app/tasks/ton_price_updater.py root@shelloch.xyz:/opt/shell/app/tasks/
scp server/app/routers/admin.py root@shelloch.xyz:/opt/shell/app/routers/

# 3. Обновляем БД
echo "🔧 Обновление БД..."
ssh root@shelloch.xyz "cd /opt/shell && venv/bin/python -c 'from app.database.db import init_db; init_db()'"

# 4. Билд клиента
echo "🔨 Билд клиента..."
ssh root@shelloch.xyz "cd /opt/shell/client && npm run build"

# 5. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 6. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 5

# 7. Проверяем статус
echo ""
echo "✓ Проверка статуса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "🎯 Изменения:"
echo ""
echo "1️⃣  Кнопки в модальном окне подарка:"
echo "   ✓ Кнопки 50/50"
echo "   ✓ Шрифты уменьшены для компактности"
echo "   ✓ Цена берется с сервера (актуальная)"
echo ""
echo "2️⃣  TabBar:"
echo "   ✓ Убрано поднятие плитки"
echo "   ✓ Убрано увеличение иконки"
echo ""
echo "3️⃣  Админка:"
echo "   ✓ Переименована в 'Настройки'"
echo "   ✓ Добавлено поле 'Наценка на подарки (%)'  "
echo "   ✓ По умолчанию: 10%"
echo "   ✓ При изменении - моментальный пересчет цен"
echo ""
echo "4️⃣  Система цен:"
echo "   ✓ Цена TON (CoinMarketCap)"
echo "   ✓ Цена с Tonnel (в TON)"
echo "   ✓ Комиссия (настраиваемая)"
echo "   ✓ Итоговая цена = (ton_price × ton_usd ÷ 0.75 × 50) × (1 + commission/100)"
