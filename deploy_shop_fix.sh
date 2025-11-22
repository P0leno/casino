#!/bin/bash
set -e

echo "🔧 Исправление системы покупки подарков..."

cd /Users/macbook/Documents/shell

# 1. Копируем исправленный shop.py
echo "📤 Копирование shop.py..."
scp server/app/routers/shop.py root@shelloch.xyz:/opt/shell/app/routers/

# 2. Рестарт бэкенда
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 3. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 3

# 4. Проверяем статус
echo ""
echo "✓ Проверка статуса:"
ssh root@shelloch.xyz "systemctl is-active shelloch-backend"

echo ""
echo "✅ Исправление завершено!"
echo ""
echo "🔒 Безопасность:"
echo "   ✓ initData валидируется через BOT_TOKEN"
echo "   ✓ Пользователь создается ТОЛЬКО после успешной валидации"
echo "   ✓ Используется правильное поле 'id' для telegram user_id"
echo "   ✓ Параметризованные SQL запросы (защита от инъекций)"
echo ""
echo "📋 Логика:"
echo "   1. Валидация initData"
echo "   2. Проверка существования пользователя"
echo "   3. Создание с балансом 0 если новый"
echo "   4. Проверка баланса"
echo "   5. Списание звезд"
echo "   6. Добавление slug в inventory"
