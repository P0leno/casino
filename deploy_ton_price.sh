#!/bin/bash
set -e

echo "🚀 Деплой системы цен с CoinMarketCap..."

cd /Users/macbook/Documents/shell

# 1. Копируем все файлы
echo "📤 Копирование файлов..."
scp server/app/database/db.py root@shelloch.xyz:/root/shell/server/app/database/
scp server/app/run.py root@shelloch.xyz:/root/shell/server/app/
scp server/app/tasks/price_updater.py root@shelloch.xyz:/root/shell/server/app/tasks/
scp server/app/tasks/ton_price_updater.py root@shelloch.xyz:/root/shell/server/app/tasks/

# 2. Обновляем .env с API ключом
echo ""
echo "🔑 Проверка COINMARKETCAP_API_KEY в .env..."
if grep -q "COINMARKETCAP_API_KEY" server/.env; then
    echo "✅ COINMARKETCAP_API_KEY найден в локальном .env"
    scp server/.env root@shelloch.xyz:/root/shell/server/.env
else
    echo "⚠️  COINMARKETCAP_API_KEY не найден в server/.env"
    echo "   Добавьте: COINMARKETCAP_API_KEY=your_key_here"
fi

# 3. Обновляем БД структуру
echo ""
echo "🔧 Обновление БД (добавление ton_price_usd)..."
ssh root@shelloch.xyz "cd /root/shell/server && venv/bin/python -c 'from app.database.db import init_db; init_db()'"

# 4. Проверяем настройки в БД
echo ""
echo "✅ Настройки в БД:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db \"SELECT key, value, description FROM settings;\""

# 5. Проверяем колонки в shop_gifts
echo ""
echo "📋 Колонки shop_gifts:"
ssh root@shelloch.xyz "cd /root/shell/server && sqlite3 users.db \"PRAGMA table_info(shop_gifts);\" | grep -E '(ton_price|price_update)'"

# 6. Перезапускаем бэкенд
echo ""
echo "🔄 Рестарт бэкенда..."
ssh root@shelloch.xyz "systemctl restart shelloch-backend"

# 7. Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 5

# 8. Проверяем логи запуска
echo ""
echo "📋 Логи первоначальной загрузки:"
ssh root@shelloch.xyz "journalctl -u shelloch-backend -n 100 --no-pager | grep -E '(ПЕРВОНАЧАЛЬНАЯ|Парсинг подарков|Обновление цены TON|Обновление цен LIMITED|Пересчет цен|ЗАВЕРШЕНА|Запущен)'"

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📊 Система обновления цен:"
echo ""
echo "🚀 При старте сервера (последовательно):"
echo "   1️⃣  Парсинг подарков (Pyrogram) → получение LIMITED NFT"
echo "   2️⃣  Обновление цены TON (CoinMarketCap)"
echo "   3️⃣  Обновление цен в TON (Tonnel) → минимальные цены"
echo "   4️⃣  Пересчет цен в звезды"
echo ""
echo "🔄 Циклические задачи:"
echo "   • Парсинг подарков: каждые 5 минут"
echo "   • Курс TON + пересчет звезд: каждые 5 минут"
echo "   • Цены с Tonnel: каждый час"
echo ""
echo "📐 Формула: ceil((ton_price × ton_usd ÷ 0.75) × 50)"
echo "   50 звезд = \$0.75"
echo ""
echo "💾 Хранение:"
echo "   • shop_gifts.ton_price - цена в TON (с Tonnel)"
echo "   • shop_gifts.price - цена в звездах (пересчитывается)"
echo "   • settings.ton_price_usd - курс TON (с CoinMarketCap)"
