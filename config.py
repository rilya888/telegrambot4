"""
Конфигурация для Telegram бота анализа калорий
"""
import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токены и API ключи
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEBUS_API_KEY = os.getenv("NEBUS_API_KEY")
NEBUS_API_URL = "https://api.studio.nebius.com/v1/"

# Проверка наличия токенов
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")
if not NEBUS_API_KEY:
    raise ValueError("NEBUS_API_KEY не найден в переменных окружения!")

# Настройки базы данных
DATABASE_PATH = "users.db"

# Настройки API
API_TIMEOUT = 30
API_CACHE_SIZE = 50  # Уменьшили размер кэша для экономии памяти
IMAGE_MAX_SIZE = (800, 800)  # Уменьшили размер для экономии трафика
IMAGE_QUALITY = 75  # Немного снизили качество для экономии трафика

# Настройки валидации
VALIDATION_LIMITS = {
    "age": {"min": 10, "max": 120},
    "height": {"min": 100, "max": 250},
    "weight": {"min": 30, "max": 300},
    "name": {"min_length": 2, "max_length": 50}
}

# Настройки логирования
def setup_logging():
    """Настройка системы логирования"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
    # Уменьшаем количество логов от внешних библиотек
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Уровни активности для расчета калорий
ACTIVITY_LEVELS = {
    'сидячая работа': 1.2,
    'легкая активность': 1.375,
    'умеренная активность': 1.55,
    'высокая активность': 1.725,
    'физическая работа': 1.9
}

# Эмодзи для типов приемов пищи
MEAL_EMOJIS = {
    'breakfast': '🌅',
    'lunch': '🍽️',
    'dinner': '🌙',
    'snack': '🍎'
}

# Эмодзи для уровней активности
ACTIVITY_EMOJIS = {
    'сидячая работа': '🏢',
    'легкая активность': '🚶',
    'умеренная активность': '🏃',
    'высокая активность': '💪',
    'физическая работа': '🏗️'
}
