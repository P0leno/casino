# Исправление логирования в parse_gifts()

## Проблема
`parse_gifts()` не добавляет подарки в БД (БД пустая), но нет логов о том, сколько подарков получено из Telegram.

## Изменения в server/app/tasks/gift_parser.py

### 1. Добавить счетчик total_received после gifts_count = 0:

```python
gifts_count = 0
skipped_count = 0
total_received = 0  # <-- ДОБАВИТЬ ЭТУ СТРОКУ

print("📡 Получение подарков из Telegram...")  # <-- ДОБАВИТЬ

try:
    async for gift in app.get_chat_gifts(
        chat_id=me.id,
        exclude_unlimited=True,
        limit=100
    ):
        total_received += 1  # <-- ДОБАВИТЬ в начале цикла
        
        # ВАЖНО: Сохраняем только подарки с transfer_price
        transfer_price = getattr(gift, 'transfer_price', None)
```

### 2. Добавить print после conn.close():

```python
conn.commit()
conn.close()

print(f"📊 Получено из Telegram: {total_received}, обработано: {gifts_count}, пропущено: {skipped_count}")  # <-- ДОБАВИТЬ

if gifts_count > 0:
```

### 3. Добавить логи в INSERT/UPDATE:

После INSERT:
```python
print(f"  ➕ Добавлен: {title} ({model_name})")
```

После UPDATE:
```python
print(f"  ✏️  Обновлен: {title} ({model_name})")
```

## Как применить на сервере:

```bash
# Редактировать файл
nano /var/www/shell/server/app/tasks/gift_parser.py

# Найти строку "gifts_count = 0" и добавить после нее:
# skipped_count = 0
# total_received = 0  # <-- НОВАЯ СТРОКА
# 
# print("📡 Получение подарков из Telegram...")  # <-- НОВАЯ СТРОКА

# Найти "async for gift in app.get_chat_gifts" и добавить в НАЧАЛЕ цикла:
# total_received += 1  # <-- НОВАЯ СТРОКА

# Найти "conn.close()" и добавить ПОСЛЕ:
# print(f"📊 Получено из Telegram: {total_received}, обработано: {gifts_count}, пропущено: {skipped_count}")

# Перезапустить
sudo systemctl restart shelloch-backend
```

## Ожидаемый результат в логах:

```
📡 Получение подарков из Telegram...
  ➕ Добавлен: Happy Brownie (Baby Carrot)
  ➕ Добавлен: Stellar Rocket (Galaxy Red)
📊 Получено из Telegram: 50, обработано: 6, пропущено: 44
✅ Обработано подарков: 6 (пропущено без transfer_price: 44)
```

Если `total_received = 0`, значит проблема в Pyrogram подключении.
Если `total_received > 0` но `gifts_count = 0`, значит у всех `transfer_price = None`.
