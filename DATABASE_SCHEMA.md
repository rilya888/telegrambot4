# Структура данных в базе данных

## Таблица `users`

При регистрации пользователя в базу данных заносятся следующие поля:

### Основные поля таблицы:
```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,           -- ID пользователя в Telegram
    username VARCHAR(255),                -- @username в Telegram
    name VARCHAR(255),                    -- Имя, введенное при регистрации
    gender VARCHAR(10),                   -- Пол: "мужской" или "женский"
    age INTEGER,                          -- Возраст
    height REAL,                          -- Рост в см
    weight REAL,                          -- Вес в кг
    daily_calories INTEGER,               -- Рассчитанная суточная норма калорий
    created_at TIMESTAMP,                 -- Дата создания записи
    updated_at TIMESTAMP                  -- Дата последнего обновления
);
```

### Процесс заполнения данных:

1. **Инициализация** (при нажатии "Регистрация"):
   ```python
   user_data = {
       'user_id': user_id,                    # Из Telegram
       'username': query.from_user.username   # Из Telegram
   }
   ```

2. **Шаг 1 - Имя**:
   ```python
   user_data['name'] = text  # Пользователь вводит имя
   ```

3. **Шаг 2 - Пол**:
   ```python
   user_data['gender'] = "мужской" | "женский"  # Выбор из кнопок
   ```

4. **Шаг 3 - Возраст**:
   ```python
   user_data['age'] = int(text)  # Пользователь вводит возраст
   ```

5. **Шаг 4 - Рост**:
   ```python
   user_data['height'] = float(text)  # Пользователь вводит рост в см
   ```

6. **Шаг 5 - Вес**:
   ```python
   user_data['weight'] = float(text)  # Пользователь вводит вес в кг
   ```

7. **Расчет калорий**:
   ```python
   user_data['daily_calories'] = db.calculate_daily_calories(
       gender, age, height, weight
   )
   ```

### Пример полных данных пользователя:

```python
{
    'user_id': 123456789,
    'username': 'user123',
    'name': 'Иван Петров',
    'gender': 'мужской',
    'age': 30,
    'height': 180.0,
    'weight': 75.0,
    'daily_calories': 2350
}
```

### Сохранение в базу:

Данные сохраняются через метод `db.add_user(user_data)`, который:
- Для PostgreSQL: использует `INSERT ... ON CONFLICT DO UPDATE`
- Для SQLite: использует `INSERT OR REPLACE`

### Автоматические поля:

- `created_at` - устанавливается автоматически при создании
- `updated_at` - обновляется при каждом изменении записи

## Таблица `calorie_history`

Эта таблица хранит историю потребления калорий пользователями:

### Структура таблицы:
```sql
CREATE TABLE calorie_history (
    id SERIAL PRIMARY KEY,              -- Уникальный ID записи
    user_id BIGINT,                     -- ID пользователя (FK к users)
    food_name TEXT,                     -- Название блюда
    calories INTEGER,                   -- Количество калорий
    source TEXT,                        -- Источник (image/text/voice)
    created_at TIMESTAMP                -- Дата создания записи
);
```

### Пример записи:
```python
{
    'id': 1,
    'user_id': 123456789,
    'food_name': 'Борщ с мясом',
    'calories': 250,
    'source': 'image',
    'created_at': '2024-01-15 14:30:00'
}
```

### Индексы:
- `idx_calorie_history_user_id` - для быстрого поиска по пользователю
