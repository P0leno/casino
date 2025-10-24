# shell
tg mini app

## Структура проекта

```
shell/
├── client/          # React фронтенд (Vite)
├── server/          # FastAPI бэкенд
└── apache-config/   # Конфигурация Apache
```

## Разработка

### Фронтенд (client/)
```bash
cd client
npm install
npm run dev
```

### Бэкенд (server/)
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 3779

# Или просто:
./start.sh
```

## Деплой на сервер

### Архитектура

- **Фронтенд**: `shelloch.xyz` - статические файлы через Apache
- **API**: `api.shelloch.xyz` - проксируется на FastAPI (порт 3779)

### Быстрый старт (без SSL)

1. Установить Apache и включить модули:
```bash
sudo apt update
sudo apt install apache2
sudo a2enmod proxy proxy_http rewrite ssl headers
```

2. Настроить DNS (добавить A-записи):
```
shelloch.xyz        -> IP сервера
www.shelloch.xyz    -> IP сервера
api.shelloch.xyz    -> IP сервера
```

3. Скопировать проект на сервер:
```bash
sudo mkdir -p /var/www/shell
cd /var/www/shell
git clone <your-repo> .
```

4. Собрать фронтенд:
```bash
cd client
npm install
npm run build
mv dist/* ../  # Переместить билд в корень /var/www/shell
cd ..
```

5. Настроить бэкенд:
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

6. Установить конфиги Apache (без SSL):

**Вариант A: Копирование**
```bash
sudo cp apache-config/shelloch.xyz-no-ssl.conf /etc/apache2/sites-available/shelloch.xyz.conf
sudo a2ensite shelloch.xyz.conf
sudo cp apache-config/api.shelloch.xyz-no-ssl.conf /etc/apache2/sites-available/api.shelloch.xyz.conf
sudo a2ensite api.shelloch.xyz.conf
sudo systemctl restart apache2
```

**Вариант B: Вручную через nano**
```bash
# Фронтенд
sudo nano /etc/apache2/sites-available/shelloch.xyz.conf
# Вставить содержимое из apache-config/shelloch.xyz-no-ssl.conf (Ctrl+O, Ctrl+X)
sudo a2ensite shelloch.xyz.conf

# API
sudo nano /etc/apache2/sites-available/api.shelloch.xyz.conf
# Вставить содержимое из apache-config/api.shelloch.xyz-no-ssl.conf (Ctrl+O, Ctrl+X)
sudo a2ensite api.shelloch.xyz.conf

sudo systemctl restart apache2
```

7. Запустить API сервис:

**Вариант A: Бэкенд в /opt/shell/ (рекомендуется)**
```bash
# Установить всё по инструкции
# См. apache-config/SYSTEMD-SETUP.md
```

**Вариант B: Бэкенд в /var/www/shell/server**
```bash
sudo cp apache-config/shelloch-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start shelloch-api
sudo systemctl enable shelloch-api
```

### Установка SSL сертификатов

После базовой настройки получить сертификаты:
```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d shelloch.xyz -d www.shelloch.xyz -d api.shelloch.xyz
```

Затем заменить конфиги на HTTPS версии:

**Вариант A: Копирование**
```bash
sudo cp apache-config/shelloch.xyz.conf /etc/apache2/sites-available/shelloch.xyz.conf
sudo cp apache-config/api.shelloch.xyz.conf /etc/apache2/sites-available/api.shelloch.xyz.conf
sudo systemctl restart apache2
```

**Вариант B: Замена через nano**
```bash
# Фронтенд - удалить и создать заново
sudo rm /etc/apache2/sites-available/shelloch.xyz.conf
sudo nano /etc/apache2/sites-available/shelloch.xyz.conf
# Вставить содержимое из apache-config/shelloch.xyz.conf (Ctrl+O, Ctrl+X)

# API - удалить и создать заново
sudo rm /etc/apache2/sites-available/api.shelloch.xyz.conf
sudo nano /etc/apache2/sites-available/api.shelloch.xyz.conf
# Вставить содержимое из apache-config/api.shelloch.xyz.conf (Ctrl+O, Ctrl+X)

# Проверить и перезапустить
sudo apache2ctl configtest
sudo systemctl restart apache2
```

### Подробная документация

Полная документация по настройке и деплою находится в [apache-config/README.md](apache-config/README.md)
