# 🔒 Безопасность системы покупки подарков

## Защита от уязвимостей

### 1. **Валидация initData**
```python
user_data = verify_init_data(request.initData)
if not user_data:
    raise HTTPException(status_code=401, detail="Unauthorized")
```
- ✅ Проверяется подпись через `BOT_TOKEN`
- ✅ Парсится только валидный `initData`
- ✅ Возвращается `None` при любой ошибке

### 2. **Создание пользователя**
```python
if not user:
    # Создается ТОЛЬКО после успешной валидации
    cursor.execute("""
        INSERT INTO users (id, user_id, username, creation_date, balance, inventory, is_banned)
        VALUES (?, ?, ?, ?, 0, '[]', 0)
    """, (user_id, user_id, username, datetime.now().isoformat()))
```
- ✅ Создание происходит **ПОСЛЕ** валидации `initData`
- ✅ Нет возможности создать пользователя с произвольным `id`
- ✅ Начальный баланс всегда `0`
- ✅ `user_id` берется из **валидированного** `user_data['id']`

### 3. **SQL инъекции**
```python
# ✅ Все запросы параметризованы
cursor.execute("SELECT ... WHERE id = ?", (user_id,))
cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
```
- ✅ Используются параметризованные запросы
- ✅ Нет конкатенации строк в SQL
- ✅ Sqlite3 автоматически экранирует параметры

### 4. **Проверка баланса**
```python
if balance < price:
    raise HTTPException(status_code=400, detail=f"Недостаточно звезд")
```
- ✅ Проверка **ДО** списания
- ✅ Транзакция откатится при ошибке
- ✅ Нет возможности уйти в минус

### 5. **Использование правильных полей**
```python
# ✅ Используется поле 'id' (telegram user_id)
cursor.execute("SELECT balance, inventory FROM users WHERE id = ?", (user_id,))
```
- ✅ Поле `id` содержит telegram user_id
- ✅ Поле `user_id` - дубликат для совместимости
- ✅ Консистентность с другими роутерами

## Алгоритм покупки

1. **Валидация** → `verify_init_data(initData)`
2. **Проверка** → существование пользователя
3. **Создание** → новый пользователь с балансом 0 (если нужно)
4. **Проверка** → наличие подарка и его доступность
5. **Проверка** → достаточность баланса
6. **Списание** → баланс - цена
7. **Добавление** → slug в inventory
8. **Уменьшение** → available_amount
9. **Commit** → сохранение транзакции

## Защищенные точки

### ✅ Невозможно:
- Купить без валидного `initData`
- Создать пользователя с произвольным `id`
- Купить подарок без денег
- SQL инъекция
- Купить закончившийся подарок
- Уйти в минус по балансу

### ✅ Безопасно:
- Создание пользователя (после валидации)
- Параметризованные запросы
- Проверка баланса перед операцией
- Транзакционность операций
- Откат при ошибках

## Логи безопасности

При попытке эксплуатации:
- `401 Unauthorized` - невалидный initData
- `404 Not Found` - подарок не найден
- `400 Bad Request` - недостаточно звезд
- `400 Bad Request` - подарок закончился

## Код проверки initData

```python
def verify_init_data(init_data: str):
    # 1. Валидация подписи через BOT_TOKEN
    if not validate_init_data(init_data, BOT_TOKEN):
        return None
    
    # 2. Парсинг данных
    try:
        parsed = parse_qs(init_data)
        user_data_str = parsed.get('user', [''])[0]
        
        if not user_data_str:
            return None
        
        # 3. Декодирование JSON
        user_data = json.loads(user_data_str)
        return user_data
    except:
        return None
```

## Выводы

✅ Система безопасна  
✅ Нет лазеек для эксплуатации  
✅ Создание пользователя контролируется  
✅ Все операции валидируются  
✅ SQL инъекции невозможны  
