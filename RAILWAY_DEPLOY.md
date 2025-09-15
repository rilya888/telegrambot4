# Быстрый деплой на Railway

## Пошаговая инструкция

### 1. Подготовка репозитория
```bash
# Инициализация Git (если еще не сделано)
git init
git add .
git commit -m "Initial commit"

# Создание репозитория на GitHub
# Затем:
git remote add origin https://github.com/yourusername/telegrambot4.git
git push -u origin main
```

### 2. Создание проекта на Railway

1. Зайдите на [railway.app](https://railway.app)
2. Нажмите "Login" → "Login with GitHub"
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий `telegrambot4`

### 3. Настройка переменных окружения

В панели Railway:
1. Перейдите в ваш проект
2. Нажмите на сервис (ваш бот)
3. Перейдите в раздел "Variables"
4. Добавьте переменные:

```
BOT_TOKEN=your_telegram_bot_token_here
NEBUS_API_KEY=your_nebius_api_key_here
```

### 4. Добавление базы данных

1. В панели проекта нажмите "New"
2. Выберите "Database" → "PostgreSQL"
3. Railway автоматически создаст `DATABASE_URL`

### 5. Проверка деплоя

1. Railway автоматически начнет деплой
2. Перейдите в раздел "Deployments"
3. Проверьте логи на наличие ошибок
4. Если все хорошо, бот будет работать!

## Структура файлов для Railway

```
telegrambot4/
├── bot.py                 # Основной файл бота (оптимизированный)
├── database.py           # Универсальная база данных (SQLite/PostgreSQL)
├── api_client.py         # Клиент для работы с Nebius API
├── config.py             # Конфигурация
├── utils.py              # Утилиты
├── requirements.txt      # Зависимости Python
├── Procfile             # Конфигурация для Railway
├── railway.json         # Дополнительная конфигурация Railway
├── .gitignore           # Игнорируемые файлы
├── env.example          # Пример переменных окружения
├── README.md            # Документация
├── OPTIMIZATIONS_APPLIED.md  # Описание оптимизаций
└── OPTIMIZATION_REPORT.md    # Отчет об оптимизации
```

## Возможные проблемы

### Ошибка с базой данных
- Убедитесь, что PostgreSQL добавлен в проект
- Проверьте, что `DATABASE_URL` создана автоматически

### Ошибка с зависимостями
- Проверьте `requirements.txt`
- Убедитесь, что все пакеты совместимы

### Бот не отвечает
- Проверьте `BOT_TOKEN` в переменных окружения
- Убедитесь, что токен правильный и бот не заблокирован

## Мониторинг

- **Логи:** Раздел "Deployments" → выберите деплой → "View Logs"
- **Метрики:** Раздел "Metrics" для мониторинга производительности
- **Переменные:** Раздел "Variables" для управления настройками

## Обновление бота

Просто сделайте push в GitHub:
```bash
git add .
git commit -m "Update bot"
git push origin main
```

Railway автоматически пересоберет и перезапустит бота!
