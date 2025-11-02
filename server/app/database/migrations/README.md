# Database Migrations

Миграции базы данных для добавления новых колонок и функций.

## Запуск миграций

```bash
cd /opt/shell
python3 app/database/migrations/migrate_bonus_balance.py
python3 app/database/migrations/migrate_paw_range.py
python3 app/database/migrations/migrate_gift_id.py
python3 app/database/migrations/add_bomzcase_mode.py
```

## Список миграций

### 1. migrate_bonus_balance.py
Добавляет колонку `bonus_balance` в таблицу `users` для хранения бонусных лапок.

### 2. migrate_paw_range.py
Добавляет колонки `paw_min` и `paw_max` в таблицу `gift_chances` для настройки диапазона лапок.

### 3. migrate_gift_id.py
Добавляет колонку `gift_id` в таблицу `gift_prices` для хранения ID подарков Telegram.

### 4. add_bomzcase_mode.py
Добавляет поддержку режима bomzcase для платного спина:
- Добавляет колонки `star_min` и `star_max` в таблицу `gift_chances`
- Создает записи для 6 подарков с режимом `mode='bomzcase'`
- Позволяет редактировать шансы платного спина через админку

## Проверка

После запуска миграций проверьте структуру таблиц:

```bash
sqlite3 database.db
.schema users
.schema gift_chances
.schema gift_prices
.exit
```
