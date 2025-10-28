#!/bin/bash
# Скрипт для освобождения порта 3779

PORT=3779

echo "🔍 Ищем процесс на порту $PORT..."

# Найти PID процесса
PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "✅ Порт $PORT свободен"
else
    echo "❌ Порт $PORT занят процессом PID: $PID"
    echo "Убиваем процесс..."
    kill -9 $PID
    sleep 1
    
    # Проверяем еще раз
    PID_CHECK=$(lsof -ti:$PORT)
    if [ -z "$PID_CHECK" ]; then
        echo "✅ Порт $PORT освобожден"
    else
        echo "⚠️ Не удалось освободить порт"
    fi
fi
