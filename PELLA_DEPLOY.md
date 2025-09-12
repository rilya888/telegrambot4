# Развертывание на pella.app

## 🚀 Быстрый деплой на pella.app

### 1. Подготовка репозитория

Убедитесь, что код загружен в GitHub:
```bash
git add .
git commit -m "Add pella.app support"
git push origin main
```

### 2. Создание проекта на pella.app

1. Зайдите на [pella.app](https://pella.app)
2. Нажмите "Login" → "Login with GitHub"
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий `rilya888/telegrambot4`

### 3. Настройка переменных окружения

В панели pella.app:
1. Перейдите в ваш проект
2. Нажмите на сервис (ваш бот)
3. Перейдите в раздел "Environment Variables"
4. Добавьте переменные:

```
BOT_TOKEN=your_telegram_bot_token_here
NEBUS_API_KEY=your_nebius_api_key_here
```

### 4. Настройка базы данных

1. В панели проекта нажмите "Add Service"
2. Выберите "PostgreSQL"
3. Скопируйте `DATABASE_URL` из настроек PostgreSQL
4. Добавьте `DATABASE_URL` в переменные окружения

### 5. Деплой

1. Нажмите "Deploy"
2. Дождитесь завершения сборки
3. Проверьте логи в разделе "Logs"

### 6. Проверка работы

1. Health check: `https://your-app.pella.app/health`
2. Главная страница: `https://your-app.pella.app/`
3. Протестируйте бота в Telegram

## 📁 Файлы для pella.app

- ✅ `bot.py` - основной файл бота с Flask health check
- ✅ `database_railway.py` - база данных для PostgreSQL
- ✅ `requirements.txt` - все зависимости Python
- ✅ `pella.yaml` - конфигурация для pella.app
- ✅ `.gitignore` - игнорируемые файлы

## 🔧 Особенности pella.app

- **Автоматический деплой:** При каждом push в GitHub
- **PostgreSQL:** Автоматически настроенная база данных
- **Health Check:** Встроенный мониторинг
- **Переменные окружения:** Безопасное хранение токенов
- **Логи:** Просмотр в реальном времени

## 🆘 Решение проблем

### Проблема: Бот не запускается
- Проверьте переменные окружения
- Убедитесь, что `BOT_TOKEN` и `NEBUS_API_KEY` установлены
- Проверьте логи в панели pella.app

### Проблема: База данных не работает
- Убедитесь, что `DATABASE_URL` установлен
- Проверьте, что PostgreSQL сервис запущен
- Проверьте логи базы данных

### Проблема: Health check не отвечает
- Убедитесь, что порт 8000 открыт
- Проверьте, что Flask приложение запускается
- Проверьте логи приложения
