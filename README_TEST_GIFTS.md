# Тестовый скрипт отправки подарков

## Описание
Скрипт для тестирования отправки Telegram подарков через pyrofork.

## Требования
```bash
pip install pyrofork python-dotenv
```

## Настройка

1. Убедитесь что в `server/.env` есть:
```env
API_ID=ваш_api_id
API_HASH=ваш_api_hash
SESSION_STRING=ваш_session_string  # опционально
```

2. Если SESSION_STRING нет, скрипт создаст новую сессию при первом запуске

## Запуск

```bash
cd /Users/macbook/Documents/shell
python3 test_gift_sender.py
```

## Настройки в скрипте

Отредактируйте эти переменные в `test_gift_sender.py`:

```python
TARGET_USER_ID = 765764130  # ID получателя
GIFT_ID = 5170233102089322756  # ID подарка (мишка)
DELAY_SECONDS = 2  # Задержка между отправками (секунды)
```

## Остановка

Нажмите `Ctrl+C` для остановки скрипта

## Примечания

- Скрипт автоматически остановится после 5 ошибок подряд
- Все подарки отправляются от вашего имени (hide_my_name=False)
- Сессия сохраняется в папке `./sessions/` если SESSION_STRING не указан
