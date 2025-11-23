# Исправление режима технических работ

## Обнаруженные проблемы:

1. ❌ `maintenance_mode` не найдена в settings БД
2. ❌ `ADMIN_IDS` пустой (читается из .env)

## Решение:

### 1. Добавить maintenance_mode в БД на сервере:

```bash
cd /opt/shell
sqlite3 users.db "INSERT OR IGNORE INTO settings (key, value, description) VALUES ('maintenance_mode', '0', 'Режим технических работ (0/1)');"
```

### 2. Проверить ADMIN_IDS в .env:

```bash
cat /opt/shell/.env | grep ADMIN_IDS
```

Должно быть:
```
ADMIN_IDS=1234567,7654321
```

Если нет - добавить:
```bash
echo "ADMIN_IDS=ваш_telegram_id" >> /opt/shell/.env
```

### 3. Узнать свой Telegram ID:

Отправьте `/start` боту @userinfobot и скопируйте ID

### 4. Перезапустить сервер:

```bash
sudo systemctl restart shelloch-backend
```

### 5. Проверить что всё работает:

```bash
# Проверить БД
sqlite3 /opt/shell/users.db "SELECT key, value FROM settings WHERE key = 'maintenance_mode';"

# Проверить логи
sudo journalctl -u shelloch-backend -f | grep -E "MAINTENANCE|ADMIN_IDS"
```

## Как работает после исправления:

### ✅ Админ (user_id в ADMIN_IDS):
- Проходит validate
- Все запросы работают
- Может переключить режим в настройках

### ✅ Пользователь (при maintenance_mode=1):
- Получает 503 от validate
- Видит экран "Технические работы"
- Все запросы блокируются

## Включить режим технических работ:

```bash
sqlite3 /opt/shell/users.db "UPDATE settings SET value = '1' WHERE key = 'maintenance_mode';"
```

## Выключить:

```bash
sqlite3 /opt/shell/users.db "UPDATE settings SET value = '0' WHERE key = 'maintenance_mode';"
```
