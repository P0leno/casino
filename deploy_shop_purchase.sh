#!/bin/bash
set -e

echo "🛍️  Деплой системы покупки подарков..."

cd /Users/macbook/Documents/shell

# 1. Копируем файлы клиента
echo "📤 Копирование файлов клиента..."
scp client/src/components/GiftDetailsModal.jsx root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/GiftDetailsModal.css root@shelloch.xyz:/root/shell/client/src/components/
scp client/src/components/Shop.jsx root@shelloch.xyz:/root/shell/client/src/components/

# 2. Копируем файлы сервера
echo "📤 Копирование файлов сервера..."
scp server/app/routers/auth.py root@shelloch.xyz:/root/shell/server/app/routers/
scp server/app/routers/shop.py root@shelloch.xyz:/root/shell/server/app/routers/

# 3. Билд клиента
echo "🔨 Билд клиента..."
ssh root@shelloch.xyz "cd /root/shell/client && npm run build"

# 4. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 5. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 3

# 6. Проверяем статус
echo "✓ Статус сервиса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "🛍️  Система покупки подарков:"
echo "   • Кнопка \"Купить\" в модальном окне подарка"
echo "   • Отображение цены со звездочкой"
echo "   • Подтверждение покупки"
echo "   • Проверка баланса"
echo "   • Добавление slug в inventory"
echo "   • Уменьшение available_amount"
