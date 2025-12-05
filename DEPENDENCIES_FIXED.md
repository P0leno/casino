# ✅ Конфликт зависимостей решён!

## Проблема
Конфликт версий certifi между:
- aiocryptopay 0.4.8 (требует certifi<2024.0.0)
- curl-cffi 0.7.4 (требует certifi>=2024.2.2)

## Решение
**curl-cffi заменён на httpx**

### Изменения:

#### 1. requirements.txt
```diff
- curl-cffi>=0.7.4
+ # curl-cffi>=0.7.4  # Конфликт с aiocryptopay
+ httpx>=0.25.0       # Замена
```

#### 2. Обновлено 3 файла:
- ✅ `app/tasks/price_updater.py`
- ✅ `app/routers/inventory.py`  
- ✅ `test_tonnel_resale.py`

#### 3. Код изменён:
```python
# Было:
from curl_cffi import requests
response = requests.post(..., impersonate="chrome")

# Стало:
import httpx
response = httpx.post(...)
```

## Проверка
```bash
python3 -m pip check
# No broken requirements found. ✅
```

## Установка
```bash
cd server
python3 -m pip install -r requirements.txt
```

**Готово!** 🚀
