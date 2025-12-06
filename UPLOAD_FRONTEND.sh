#!/bin/bash

echo "🚀 Загрузка нового фронтенда на сервер"
echo ""

# Проверка что билд существует
if [ ! -d "client/dist" ]; then
    echo "❌ Папка client/dist не найдена!"
    echo "Сначала создай билд: cd client && npm run build"
    exit 1
fi

echo "Выбери способ загрузки:"
echo "1) SCP (нужен доступ с локальной машины)"
echo "2) Показать инструкции для ручной загрузки"
echo ""
read -p "Выбор (1-2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    read -p "SSH пользователь (обычно root): " ssh_user
    read -p "SSH хост (wonderfulhot.aeza.network): " ssh_host
    read -p "Путь на сервере (/var/www/shelloch): " server_path
    
    echo ""
    echo "📦 Создаю архив..."
    cd client/dist
    tar -czf ../../frontend-build.tar.gz *
    cd ../..
    
    echo "📤 Загружаю на сервер..."
    scp frontend-build.tar.gz $ssh_user@$ssh_host:/tmp/
    
    echo "📂 Распаковываю на сервере..."
    ssh $ssh_user@$ssh_host << 'ENDSSH'
cd /tmp
sudo tar -xzf frontend-build.tar.gz -C /var/www/shelloch/
sudo chown -R www-data:www-data /var/www/shelloch/
rm frontend-build.tar.gz
echo "✅ Файлы обновлены!"
ENDSSH
    
    echo ""
    echo "✅ Готово! Обнови страницу в браузере: Ctrl+Shift+R"
    
elif [ "$choice" = "2" ]; then
    echo ""
    echo "📋 Инструкции для ручной загрузки:"
    echo ""
    echo "1️⃣ Создай архив (на локальной машине):"
    echo "   cd /Users/macbook/Documents/shell/client/dist"
    echo "   tar -czf frontend-build.tar.gz *"
    echo ""
    echo "2️⃣ Загрузи через FileZilla/WinSCP/Cyberduck:"
    echo "   - Подключись к wonderfulhot.aeza.network"
    echo "   - Загрузи frontend-build.tar.gz в /tmp/"
    echo ""
    echo "3️⃣ Распакуй на сервере (через SSH):"
    echo "   cd /tmp"
    echo "   sudo tar -xzf frontend-build.tar.gz -C /var/www/shelloch/"
    echo "   sudo chown -R www-data:www-data /var/www/shelloch/"
    echo "   rm frontend-build.tar.gz"
    echo ""
    echo "4️⃣ Проверь:"
    echo "   ls -la /var/www/shelloch/assets/index-*.js"
    echo ""
    echo "5️⃣ В браузере:"
    echo "   Ctrl+Shift+R (или Cmd+Shift+R) для очистки кэша"
fi
