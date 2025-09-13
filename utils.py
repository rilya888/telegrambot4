"""
Утилиты для Telegram бота анализа калорий
"""
import re
import hashlib
import logging
from typing import Optional, Any
from telegram import Update

logger = logging.getLogger(__name__)

def validate_user_input(text: str, input_type: str) -> Optional[Any]:
    """Валидация пользовательского ввода"""
    try:
        if input_type == "age":
            age = int(text)
            if 10 <= age <= 120:
                return age
            return None
        elif input_type == "height":
            height = float(text)
            if 100 <= height <= 250:
                return height
            return None
        elif input_type == "weight":
            weight = float(text)
            if 30 <= weight <= 300:
                return weight
            return None
        elif input_type == "name":
            if 2 <= len(text) <= 50 and text.replace(" ", "").isalpha():
                return text.strip()
            return None
        return text
    except (ValueError, TypeError):
        return None

def extract_calories_from_text(text: str) -> Optional[int]:
    """Извлечение количества калорий из текста"""
    try:
        # Ищем числа в тексте
        numbers = re.findall(r'\d+', text)
        if numbers:
            # Возвращаем первое найденное число
            return int(numbers[0])
        return None
    except (ValueError, TypeError):
        return None

def format_calorie_response(calories: int, daily_sum: int, daily_calories: int) -> str:
    """Форматирование ответа с калориями"""
    if daily_calories > 0:
        percentage = (daily_sum / daily_calories) * 100
        return (f"Примерное количество калорий: {calories}\n\n"
                f"Общее количество калорий за сегодня: {daily_sum}\n\n"
                f"📊 Это составляет {percentage:.1f}% от вашей суточной нормы ({daily_calories} ккал)")
    else:
        return (f"Примерное количество калорий: {calories}\n\n"
                f"Общее количество калорий за сегодня: {daily_sum}")

async def safe_reply(update: Update, text: str, **kwargs) -> bool:
    """Безопасная отправка сообщения с обработкой ошибок"""
    try:
        if update.message:
            await update.message.reply_text(text, **kwargs)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def create_image_hash(image_data: bytes) -> str:
    """Создание хэша изображения для кэширования"""
    return hashlib.md5(image_data).hexdigest()

def create_text_hash(text: str) -> str:
    """Создание хэша текста для кэширования"""
    return hashlib.md5(text.lower().encode()).hexdigest()

def format_activity_display(activity_level: str) -> str:
    """Форматирование отображения уровня активности"""
    activity_display = {
        'сидячая работа': '🏢 Сидячая работа (офис, учеба)',
        'легкая активность': '🚶 Легкая активность (прогулки, домашние дела)',
        'умеренная активность': '🏃 Умеренная активность (спорт 3-5 раз/неделю)',
        'высокая активность': '💪 Высокая активность (спорт 6-7 раз/неделю)',
        'физическая работа': '🏗️ Физическая работа (строительство, грузчик)'
    }
    return activity_display.get(activity_level, activity_level)

def format_meal_display(meal_key: str) -> str:
    """Форматирование отображения типа приема пищи"""
    meal_display = {
        'breakfast': '🌅 Завтрак',
        'lunch': '🍽️ Обед',
        'dinner': '🌙 Ужин',
        'snack': '🍎 Перекус'
    }
    return meal_display.get(meal_key, '🍽️ Блюдо')
