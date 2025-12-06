#!/bin/bash

echo "📦 Деплой фронтенда краш игры..."
echo ""

# Билд уже создан, проверяем
if [ ! -d "client/dist" ]; then
  echo "❌ Нет папки client/dist! Запусти: cd client && npm run build"
  exit 1
fi

echo "✅ Билд найден"
echo ""
echo "Выбери способ деплоя:"
echo "1) SCP (скопировать на сервер)"
echo "2) Показать инструкции для ручного деплоя"
echo ""
read -p "Выбор (1-2): " choice

if [ "$choice" = "1" ]; then
  read -p "SSH пользователь@хост (например: user@wonderfulhot.aeza.network): " ssh_target
  read -p "Путь на сервере (например: /var/www/shelloch): " server_path
  
  echo ""
  echo "🚀 Загружаю файлы на $ssh_target:$server_path ..."
  rsync -avz --delete client/dist/ "$ssh_target:$server_path/"
  
  if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Фронтенд успешно загружен!"
    echo "🔄 Перезагрузи страницу в браузере (Ctrl+Shift+R)"
  else
    echo ""
    echo "❌ Ошибка при загрузке"
  fi
elif [ "$choice" = "2" ]; then
  echo ""
  echo "📋 Инструкции для ручного деплоя:"
  echo ""
  echo "1. Через FileZilla/Cyberduck:"
  echo "   - Подключись к серверу по SFTP"
  echo "   - Загрузи все файлы из client/dist/ в /var/www/shelloch/"
  echo ""
  echo "2. Через командную строку:"
  echo "   scp -r client/dist/* user@server:/var/www/shelloch/"
  echo ""
  echo "3. На самом сервере:"
  echo "   - git pull origin main"
  echo "   - cd client && npm run build"
  echo "   - sudo cp -r dist/* /var/www/shelloch/"
fi
