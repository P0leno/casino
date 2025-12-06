# Исправление обхода Cloudflare для Tonnel API

## Проблема
Запросы к Tonnel API блокировались Cloudflare (ошибка 403), потому что `aiohttp` не имитирует реальный браузер.

## Решение
Установлена библиотека `curl_cffi`, которая имитирует TLS fingerprint браузера Chrome и обходит защиту Cloudflare.

## Изменения

### 1. Установлена зависимость
```bash
pip install curl_cffi>=0.13.0
```

### 2. Обновлены файлы

#### server/requirements.txt
```diff
+ curl_cffi>=0.13.0
```

#### server/test_tonnel_debug.py
- Заменен `aiohttp` на `curl_cffi.requests.AsyncSession`
- Используется `impersonate="chrome"` для имитации браузера

#### server/app/tasks/price_updater.py
- Заменен `aiohttp` на `curl_cffi.requests.AsyncSession`
- Используется `impersonate="chrome"` для имитации браузера

#### server/app/routers/shop.py
- Добавлены дефолтные значения `= None` для всех Optional полей в модели `ShopGift`
- Исправлена совместимость с Pydantic 2.x

#### server/app/utils/shop_cache.py
- Добавлены отсутствующие поля в SQL запрос:
  - `symbol_name`
  - `rarity_model`
  - `rarity_symbol`
  - `rarity_backdrop`

## Результаты тестирования

### До исправления
```
📥 Статус: 403
❌ Ошибка 403 - Cloudflare блокировка
```

### После исправления
```
📥 Статус: 200
✅ Успешно! Получено объектов: 10
✅ Обновление цен завершено: 6/6
```

### Примеры обновленных цен
- Desk Calendar (Basic Blue): 2 TON
- B-Day Candle (Icicle): 2 TON
- Xmas Stocking (Vintage): 2.5 TON
- Happy Brownie (Unicorn): 2.5 TON
- Faith Amulet (Silver Gold): 2.47 TON
- Instant Ramen (Giant Crab): 1.95 TON

## Деплой на сервер

1. Обновить код на сервере:
```bash
git pull
```

2. Установить зависимости:
```bash
cd server
pip install -r requirements.txt
```

3. Перезапустить сервис:
```bash
sudo systemctl restart shelloch-backend
```

4. Проверить логи:
```bash
sudo journalctl -u shelloch-backend -f
```

## Важно
- `curl_cffi` работает только на Linux/macOS с libcurl
- Библиотека автоматически обходит Cloudflare без дополнительной настройки
- Retry логика (3 попытки) сохранена для обработки временных сбоев
