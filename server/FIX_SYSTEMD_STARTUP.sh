#!/bin/bash
# Скрипт для исправления медленного запуска systemd сервиса

echo "🔧 Исправление systemd сервиса..."

# 1. Копируем обновленный service файл
echo "📋 Копирование service файла..."
sudo cp /opt/shell/shelloch-backend.service /etc/systemd/system/

# 2. Перезагружаем systemd
echo "🔄 Перезагрузка systemd daemon..."
sudo systemctl daemon-reload

# 3. Перезапускаем сервис
echo "🚀 Перезапуск сервиса..."
sudo systemctl restart shelloch-backend

# 4. Проверяем статус
echo "✅ Проверка статуса..."
sudo systemctl status shelloch-backend --no-pager

echo ""
echo "✨ Готово! Теперь запуск должен быть быстрым (~10-15 секунд вместо 30)"
echo ""
echo "Для проверки времени запуска:"
echo "  systemd-analyze blame | grep shelloch"
