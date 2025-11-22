#!/bin/bash
set -e

echo "🎨 Исправление анимации TabBar..."

cd /Users/macbook/Documents/shell

# 1. Копируем TabBar.css
echo "📤 Копирование TabBar.css..."
scp client/src/components/TabBar.css root@shelloch.xyz:/root/shell/client/src/components/

# 2. Билд клиента
echo "🔨 Билд клиента..."
ssh root@shelloch.xyz "cd /root/shell/client && npm run build"

echo ""
echo "✅ Готово!"
echo ""
echo "Изменения:"
echo "  ✓ Убрано поднятие плитки (translateY)"
echo "  ✓ Убрано увеличение иконки (scale)"
echo "  ✓ Оставлен стеклянный эффект"
echo "  ✓ Оставлено свечение"
echo "  ✓ Иконка просто становится ярче"
