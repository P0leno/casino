# Как перезапустить TON Checker после обновления

## Быстрый перезапуск

```bash
# 1. Перейти в директорию проекта
cd /opt/shell

# 2. Обновить код
git pull origin main

# 3. Перезапустить checker
sudo systemctl restart ton-checker

# 4. Проверить что запустился
sudo systemctl status ton-checker

# 5. Смотреть логи в реальном времени
sudo journalctl -u ton-checker -f
```

## Проверка работы

После перезапуска в логах должно появиться:

```
🚀 TON Transaction Checker started
Monitoring address: UQA3XG-I...
🔍 Checking TON transactions for wallet: UQA3XG-I...
📬 Fetched X transactions from TONAPI
```

Если транзакция найдена:
```
🔍 Found transaction: 0.1 TON, comment: '2IPW8Z8Y', tx_hash: d6cdec2a...
✅ Payment confirmed! User 123456 received 550 Stars (0.1 TON)
✅ Notification sent to user 123456
```

Если инвойс не найден:
```
❌ Invoice not found for payment_code: 2IPW8Z8Y
   Pending payment codes in DB: ['ABC123XY', 'DEF456GH']
```

## Отладка транзакции

Если транзакция не обнаруживается:

### 1. Проверить что адрес правильный

```bash
grep TON_MERCHANT_ADDRESS /opt/shell/server/.env
```

Должен быть:
```
TON_MERCHANT_ADDRESS=UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y
```

### 2. Проверить транзакции через TONAPI вручную

```bash
curl "https://tonapi.io/v2/blockchain/accounts/UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y/transactions?limit=5"
```

### 3. Проверить pending инвойсы в БД

```bash
sqlite3 /opt/shell/users.db "SELECT id, user_id, payment_code, amount_ton, created_at, status FROM ton_invoices WHERE status = 'pending' ORDER BY created_at DESC LIMIT 10;"
```

### 4. Проверить конкретный payment_code

```bash
sqlite3 /opt/shell/users.db "SELECT * FROM ton_invoices WHERE payment_code = '2IPW8Z8Y';"
```

### 5. Посмотреть последние 50 строк логов

```bash
sudo journalctl -u ton-checker -n 50
```

## Тестирование с реальной транзакцией

1. **Создать тестовый инвойс** (через фронтенд):
   - Открыть приложение
   - Выбрать TON payment
   - Ввести 0.1 TON
   - Нажать "Оплатить"
   - Записать payment_code (например: `A7B3C9D2`)

2. **Проверить что инвойс в БД**:
```bash
sqlite3 /opt/shell/users.db "SELECT * FROM ton_invoices WHERE payment_code = 'A7B3C9D2';"
```

3. **Отправить TON с этим комментарием**

4. **Следить за логами**:
```bash
sudo journalctl -u ton-checker -f
```

Должно появиться:
```
🔍 Found transaction: 0.1 TON, comment: 'A7B3C9D2', tx_hash: ...
✅ Payment confirmed! User XXX received YYY Stars (0.1 TON)
```

5. **Проверить баланс пользователя**:
```bash
sqlite3 /opt/shell/users.db "SELECT id, balance FROM users WHERE id = USER_ID;"
```

## Типичные проблемы

### Транзакция есть, но не находится

**Причина**: Адрес в .env не совпадает с адресом получателя

**Решение**:
1. Проверить адрес в блокчейне (из вашей транзакции)
2. Сравнить с адресом в .env
3. Обновить .env если нужно
4. Перезапустить checker

### Payment code не совпадает

**Причина**: Регистр букв или пробелы

**Решение**: Теперь поиск регистронезависимый (UPPER), но проверьте что нет лишних пробелов

### TONAPI возвращает ошибку

**Причина**: Rate limit или неправильный формат адреса

**Решение**:
```bash
# Проверить ответ TONAPI
curl -v "https://tonapi.io/v2/blockchain/accounts/UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y/transactions?limit=1"
```

## Мониторинг

Настроить алерт если checker упал:

```bash
# Проверка каждую минуту
*/1 * * * * systemctl is-active --quiet ton-checker || echo "TON Checker is down!" | mail -s "Alert: TON Checker" admin@example.com
```

Или использовать systemd OnFailure:

```ini
[Unit]
OnFailure=notify-admin@%n.service
```
