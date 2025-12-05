# 🔴 Redis Migration - Пошаговый план внедрения

## 📋 Что уже сделано ✅

1. ✅ **Инфраструктура:**
   - `server/app/utils/redis_client.py` - клиент с connection pool
   - `server/app/utils/redis_models.py` - модели RedisUser, RedisShopGift, RedisPromo
   - `server/app/tasks/redis_sync.py` - фоновая синхронизация
   - `server/app/run.py` - добавлен graceful shutdown

2. ✅ **Документация:**
   - `REDIS_INTEGRATION.md` - архитектура и теория
   - `REDIS_EXAMPLE.md` - примеры кода
   - `REDIS_SETUP.sh` - скрипт установки

3. ✅ **Безопасность:**
   - Write-Through паттерн (SQLite → Redis)
   - Автоматический fallback на SQLite
   - Graceful shutdown с сохранением данных

---

## 🚀 Установка и тестирование

### Шаг 1: Установка Redis
```bash
# Запустить скрипт установки
chmod +x REDIS_SETUP.sh
./REDIS_SETUP.sh

# Или вручную:
# macOS:
brew install redis
brew services start redis

# Linux:
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### Шаг 2: Установка Python пакетов
```bash
pip install redis==5.0.1 hiredis==2.3.2
```

### Шаг 3: Настройка .env
```bash
# Добавить в server/.env:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SYNC_INTERVAL=300  # 5 минут
```

### Шаг 4: Тестирование подключения
```bash
# Проверить Redis
redis-cli ping
# Должно вывести: PONG

# Запустить сервер
cd server
python -m app.run

# В логах должно быть:
# ✅ Redis connected: localhost:6379
# ✅ Redis синхронизация запущена (каждые 5 минут)
```

---

## 📝 План миграции по роутерам

### Приоритет 1: Высоконагруженные эндпоинты (Первая неделя)

#### 1.1 game.py - Спины (Критично!)
**Эндпоинты для обновления:**
- `POST /api/spin` (free-spin) ⭐⭐⭐
- `POST /api/bazmin-spin` ⭐⭐⭐
- `POST /api/lapik-spin` ⭐⭐⭐
- `POST /api/sell-gift` ⭐⭐

**Изменения:**
```python
# ДО:
cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
balance = cursor.fetchone()[0]

# ПОСЛЕ:
from app.utils.redis_models import RedisUser
user = RedisUser.get(user_id)
balance = user['balance']
```

**Ожидаемый эффект:**
- Чтение баланса: 10ms → 1ms
- Нагрузка на SQLite: -80%

---

#### 1.2 shop.py - Магазин (Критично!)
**Эндпоинты:**
- `POST /api/shop/buy-gift` ⭐⭐⭐
- `GET /api/shop/gifts` ⭐⭐⭐

**Изменения:**
```python
# ДО:
cursor.execute("SELECT * FROM shop_gifts WHERE slug = ?", (slug,))
gift = cursor.fetchone()

# ПОСЛЕ:
from app.utils.redis_models import RedisShopGift
gift = RedisShopGift.get(slug)
```

**Ожидаемый эффект:**
- Загрузка магазина: 100ms → 5ms
- Проверка подарка: 20ms → 1ms

---

#### 1.3 promocode.py - Промокоды (Средний приоритет)
**Эндпоинты:**
- `POST /api/promocode/activate` ⭐⭐

**Изменения:**
```python
# ДО:
cursor.execute("SELECT * FROM promocodes WHERE promo = ?", (code,))
promo = cursor.fetchone()

# ПОСЛЕ:
from app.utils.redis_models import RedisPromo
promo = RedisPromo.get(code)
```

**Ожидаемый эффект:**
- Проверка промокода: 20ms → 1ms

---

### Приоритет 2: Средненагруженные (Вторая неделя)

#### 2.1 tasks.py - Задания
**Эндпоинты:**
- `POST /api/tasks/complete` ⭐⭐

**Изменения:**
```python
from app.utils.redis_models import RedisUser

# При начислении награды
user = RedisUser.get(user_id)
RedisUser.update_balance(user_id, balance=user['balance'] + award)
```

---

#### 2.2 inventory.py - Инвентарь
**Эндпоинты:**
- `POST /api/inventory/sell` ⭐⭐
- `GET /api/inventory` ⭐

**Изменения:**
```python
from app.utils.redis_models import RedisUser

user = RedisUser.get(user_id)
inventory = user['inventory']
# ... логика продажи
RedisUser.update(user_id, inventory=new_inventory, balance=new_balance)
```

---

#### 2.3 crash.py - Краш-игра
**Эндпоинты:**
- `POST /api/crash/bet` ⭐⭐
- `POST /api/crash/cashout` ⭐⭐

**Изменения:**
```python
from app.utils.redis_models import RedisUser

# При ставке
user = RedisUser.get(user_id)
if user['balance'] < amount:
    raise HTTPException(400, "Недостаточно средств")

RedisUser.update_balance(user_id, balance=user['balance'] - amount)

# При выигрыше
RedisUser.update_balance(user_id, balance=user['balance'] + winnings)
```

---

### Приоритет 3: Низконагруженные (По необходимости)

#### 3.1 auth.py - Аутентификация
**Эндпоинты:**
- `POST /api/validate` ⭐

**Примечание:** Кэшировать аккуратно, только is_banned status

#### 3.2 admin.py - Админка
**Эндпоинты:**
- Добавить `/admin/redis-stats` для мониторинга

---

## 🧪 Тестирование после каждого роутера

### 1. Функциональный тест
```bash
# Проверить что эндпоинт работает
curl -X POST http://localhost:8000/api/spin \
  -H "Content-Type: application/json" \
  -d '{"initData": "..."}'
```

### 2. Проверка Redis
```bash
# Посмотреть что попало в Redis
redis-cli KEYS "user:*"
redis-cli GET "user:123456"
```

### 3. Проверка fallback
```bash
# Остановить Redis
redis-cli SHUTDOWN

# Проверить что API работает (через SQLite)
curl http://localhost:8000/api/spin

# Запустить Redis обратно
redis-server
```

### 4. Нагрузочный тест
```bash
# До Redis:
ab -n 1000 -c 10 http://localhost:8000/api/spin

# После Redis:
ab -n 1000 -c 10 http://localhost:8000/api/spin

# Сравнить RPS (requests per second)
```

---

## 📊 Мониторинг в production

### Добавить эндпоинт мониторинга:
```python
# server/app/routers/admin.py

from app.utils.redis_client import cache
from app.tasks.redis_sync import sync_manager

@router.get("/admin/redis-stats")
async def redis_stats(user_data = Depends(verify_admin)):
    return {
        "redis": cache.get_info(),
        "sync": sync_manager.get_stats()
    }
```

### Метрики для отслеживания:
1. **Cache Hit Rate** - % запросов из Redis
2. **Memory Usage** - использование памяти Redis
3. **Sync Lag** - задержка синхронизации
4. **Errors** - количество ошибок

---

## ⚠️ Что делать при проблемах

### Проблема 1: Redis connection timeout
```bash
# Увеличить timeout в .env
REDIS_SOCKET_TIMEOUT=10
```

### Проблема 2: Redis out of memory
```bash
# Проверить память
redis-cli INFO memory

# Уменьшить TTL или увеличить лимит
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Проблема 3: Старые данные в кэше
```python
# Принудительно invalidate
from app.utils.redis_models import RedisUser
RedisUser.invalidate(user_id)

# Или полностью очистить
redis-cli FLUSHDB
```

### Проблема 4: Redis упал - как восстановить?
```bash
# 1. Запустить Redis
redis-server

# 2. Перезапустить сервер (загрузит данные из SQLite)
python server/app/run.py

# 3. Данные автоматически загрузятся при первых запросах
```

---

## 🎯 Ожидаемые результаты

### Производительность:
| Операция | До Redis | После Redis | Улучшение |
|----------|----------|-------------|-----------|
| Чтение баланса | 10ms | 1ms | **10x** |
| Проверка промокода | 20ms | 1ms | **20x** |
| Загрузка магазина | 100ms | 5ms | **20x** |
| RPS (requests/sec) | 200 | 1000+ | **5x** |

### Масштабируемость:
- До: ~200 одновременных пользователей
- После: **1000+** одновременных пользователей

### Стабильность:
- ✅ Автоматический fallback на SQLite
- ✅ Graceful shutdown без потери данных
- ✅ Синхронизация каждые 5 минут

---

## ✅ Чеклист внедрения

### Подготовка:
- [ ] Установить Redis
- [ ] Установить Python пакеты
- [ ] Настроить .env
- [ ] Запустить сервер и проверить логи

### Миграция (по роутерам):
- [ ] game.py - спины
- [ ] shop.py - магазин
- [ ] promocode.py - промокоды
- [ ] tasks.py - задания
- [ ] inventory.py - инвентарь
- [ ] crash.py - краш-игра

### Тестирование:
- [ ] Функциональные тесты
- [ ] Проверка Redis
- [ ] Тест fallback (остановить Redis)
- [ ] Нагрузочный тест
- [ ] Тест graceful shutdown

### Production:
- [ ] Добавить мониторинг
- [ ] Настроить алерты
- [ ] Документировать процедуры

---

## 🚀 Начать сейчас!

```bash
# 1. Установка
./REDIS_SETUP.sh

# 2. Тест подключения
redis-cli ping

# 3. Запуск сервера
python server/app/run.py

# 4. Проверка логов
# Должно быть: ✅ Redis синхронизация запущена

# 5. Первый роутер - game.py
# Следуй примерам из REDIS_EXAMPLE.md
```

**Готов начать?** Начни с game.py - он даст максимальный прирост производительности! 🚀
