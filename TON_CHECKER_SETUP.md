# TON Checker Setup Guide

## Установка и запуск TON Transaction Checker

### 1. Установка зависимостей

```bash
cd /opt/shell
source venv/bin/activate
pip install aiohttp==3.9.1
```

### 2. Настройка .env файла

Добавьте адрес TON кошелька для приема платежей:

```bash
nano /opt/shell/server/.env
```

Добавьте строку:
```
TON_MERCHANT_ADDRESS=ваш_адрес_ton_кошелька
```

Пример:
```
TON_MERCHANT_ADDRESS=UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y
```

### 3. Установка systemd service

```bash
# Копируем service файл
sudo cp /opt/shell/server/ton-checker.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable ton-checker

# Запускаем сервис
sudo systemctl start ton-checker
```

### 4. Проверка работы

```bash
# Статус сервиса
sudo systemctl status ton-checker

# Логи
sudo journalctl -u ton-checker -f

# Последние 50 строк логов
sudo journalctl -u ton-checker -n 50
```

### 5. Команды управления

```bash
# Остановить
sudo systemctl stop ton-checker

# Перезапустить
sudo systemctl restart ton-checker

# Отключить автозапуск
sudo systemctl disable ton-checker
```

## Как это работает

1. **Пользователь создает инвойс**:
   - Выбирает количество TON
   - Получает QR код и payment_code (8 символов)

2. **Пользователь отправляет TON**:
   - На адрес `TON_MERCHANT_ADDRESS`
   - С комментарием = `payment_code`

3. **ton_checker проверяет транзакции**:
   - Каждые 10 секунд через TONAPI
   - Ищет комментарий в транзакциях
   - Находит инвойс в БД по payment_code

4. **Начисление Stars**:
   - Получает фактическую сумму TON
   - Пересчитывает в USD по курсу из БД
   - Считает Stars: (USD / $0.015) * 1.05 (+5% бонус)
   - Начисляет Stars на баланс пользователя
   - Обновляет статус инвойса на 'confirmed'

## Таблица ton_invoices

```sql
CREATE TABLE ton_invoices (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    payment_code TEXT UNIQUE NOT NULL,  -- Комментарий для оплаты
    amount_ton REAL NOT NULL,            -- Ожидаемая сумма TON
    amount_stars_expected INTEGER,       -- Ожидаемое количество Stars
    status TEXT DEFAULT 'pending',       -- pending | confirmed
    created_at TEXT NOT NULL,
    confirmed_at TEXT,                   -- Когда подтвержден
    amount_received REAL,                -- Фактически получено TON
    amount_stars_actual INTEGER,         -- Фактически начислено Stars
    tx_hash TEXT,                        -- Хэш транзакции
    tx_lt TEXT,                          -- Logical time транзакции
    tx_timestamp INTEGER                 -- Timestamp транзакции
);
```

## Troubleshooting

### Checker не запускается

```bash
# Проверить логи
sudo journalctl -u ton-checker -n 100

# Проверить что Python может импортировать модули
cd /opt/shell/server
source /opt/shell/venv/bin/activate
python3 -c "from app.ton_checker import main"
```

### Транзакции не обнаруживаются

1. Проверьте что адрес правильный:
```bash
grep TON_MERCHANT_ADDRESS /opt/shell/server/.env
```

2. Проверьте TONAPI:
```bash
curl "https://tonapi.io/v2/blockchain/accounts/UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y/transactions?limit=5"
```

3. Проверьте что комментарий правильно передается

### Stars не начисляются

1. Проверьте что инвойс создался:
```bash
sqlite3 /opt/shell/users.db "SELECT * FROM ton_invoices ORDER BY created_at DESC LIMIT 5;"
```

2. Проверьте курс TON:
```bash
sqlite3 /opt/shell/users.db "SELECT * FROM settings WHERE key = 'ton_price_usd';"
```

## API Endpoints

### Создание инвойса
```
POST /api/ton/create-payment
{
  "initData": "...",
  "tonAmount": 1.5
}
```

Ответ:
```json
{
  "success": true,
  "tonAmount": 1.5,
  "starsAmount": 550,
  "paymentCode": "A7B3C9D2",
  "merchantAddress": "UQA3...",
  "qrCode": "data:image/png;base64,...",
  "deepLinkTon": "ton://transfer/...",
  "deepLinkTonkeeper": "tonkeeper://transfer/..."
}
```

### Расчет Stars
```
POST /api/ton/calculate-stars
{
  "initData": "...",
  "tonAmount": 1.5
}
```

Ответ:
```json
{
  "success": true,
  "stars": 550,
  "tonAmount": 1.5,
  "usdAmount": 8.25,
  "tonUsdRate": 5.5,
  "bonusPercent": 5
}
```
