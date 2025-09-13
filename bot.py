import logging
import io
import os
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
try:
    from database_railway import UserDatabase
except ImportError:
    from database import UserDatabase
import asyncio
from datetime import datetime, time
from typing import Optional, Dict, Any

# Импортируем наши модули
from config import setup_logging, API_CACHE_SIZE, BOT_TOKEN
from utils import (
    validate_user_input, extract_calories_from_text, 
    format_calorie_response, safe_reply, create_image_hash, create_text_hash
)
from api_client import api_client

# Настройка логирования
logger = setup_logging()

# Инициализация базы данных
db = UserDatabase()

# Кэш для API запросов
api_cache = {}


def analyze_food_image(image_data: bytes) -> str:
    """Анализ изображения еды через Nebius API с кэшированием"""
    try:
        # Создаем хэш изображения для кэширования
        image_hash = create_image_hash(image_data)
        
        # Проверяем кэш
        if image_hash in api_cache:
            logger.info("Using cached result for image analysis")
            return api_cache[image_hash]
        
        # Анализируем изображение через API клиент
        result_text = api_client.analyze_image(image_data)
        
        # Сохраняем в кэш (ограничиваем размер кэша)
        if len(api_cache) < API_CACHE_SIZE:
            api_cache[image_hash] = result_text
        
        return result_text
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return "Произошла ошибка при анализе изображения. Попробуйте еще раз."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    
    logger.info(f"User {user_id} ({username}) started the bot")
    
    # Проверяем, нужно ли сбросить счетчик (новый день)
    await check_and_reset_daily_meals(context)
    
    # Проверяем, зарегистрирован ли пользователь
    user = db.get_user(user_id)
    
    if not user:
        # Пользователь не зарегистрирован, начинаем регистрацию
        logger.info(f"New user {user_id} ({username}) starting registration")
        await start_registration(update, context)
    else:
        # Пользователь зарегистрирован, показываем главное меню
        logger.info(f"Existing user {user_id} ({username}) accessing main menu")
        keyboard = [
            [InlineKeyboardButton("🍽️ Добавить блюдо", callback_data="add_food")],
            [InlineKeyboardButton("🔍 Хочу знать сколько калорий", callback_data="quick_analysis")],
            [InlineKeyboardButton("📋 Меню", callback_data="main_menu_submenu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        daily_calories = user.get('daily_calories', 0)
        await update.message.reply_text(
            f"🍕 Привет, {user.get('name', 'пользователь')}!\n\n"
            f"Ваша суточная норма калорий: {daily_calories} ккал\n\n"
            f"Выберите действие:",
            reply_markup=reply_markup
        )

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало процесса регистрации"""
    keyboard = [
        [InlineKeyboardButton("📝 Начать регистрацию", callback_data="start_registration")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🍕 Добро пожаловать! Для точного расчета калорий мне нужна информация о вас.\n\n"
        "Я задам несколько вопросов о вашем возрасте, росте, весе и физической активности.\n\n"
        "Нажмите кнопку ниже, чтобы начать регистрацию:",
        reply_markup=reply_markup
    )


def analyze_food_text(text_description: str) -> str:
    """Анализ текстового описания еды через Nebius API с кэшированием"""
    try:
        # Создаем хэш текста для кэширования
        text_hash = create_text_hash(text_description)
        
        # Проверяем кэш
        if text_hash in api_cache:
            logger.info("Using cached result for text analysis")
            return api_cache[text_hash]
        
        # Анализируем текст через API клиент
        result_text = api_client.analyze_text(text_description)
        
        # Сохраняем в кэш (ограничиваем размер кэша)
        if len(api_cache) < API_CACHE_SIZE:
            api_cache[text_hash] = result_text
        
        return result_text
        
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        return "Произошла ошибка при анализе описания. Попробуйте еще раз."

def transcribe_voice(audio_data):
    """Транскрипция голосового сообщения в текст"""
    temp_ogg_path = "temp_audio.ogg"
    temp_wav_path = "temp_audio.wav"
    
    try:
        # Создаем временный файл для аудио
        with open(temp_ogg_path, "wb") as f:
            f.write(audio_data)
        
        # Конвертируем OGG в WAV
        audio = AudioSegment.from_ogg(temp_ogg_path)
        audio.export(temp_wav_path, format="wav")
        
        # Инициализируем распознаватель речи
        recognizer = sr.Recognizer()
        
        # Распознаем речь
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        
        return text
        
    except Exception as e:
        logger.error(f"Error transcribing voice: {e}")
        return None
    finally:
        # Удаляем временные файлы в любом случае
        for temp_file in [temp_ogg_path, temp_wav_path]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except OSError as e:
                logger.warning(f"Could not remove temp file {temp_file}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_registration":
        await start_registration_flow(query, context)
    elif query.data == "photo_analysis":
        meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
        await query.edit_message_text(f"📸 Отправьте мне фотографию еды для {meal_type}, и я определю количество калорий.")
    elif query.data == "text_analysis":
        meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
        await query.edit_message_text(f"📝 Опишите еду текстом для {meal_type}, и я определю количество калорий.\n\nНапример: 'Большая пицца с пепперони и сыром'")
    elif query.data == "voice_analysis":
        meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
        await query.edit_message_text(f"🎤 Отправьте мне голосовое сообщение с описанием еды для {meal_type}, и я определю количество калорий.\n\nНапример, скажите: 'Большая пицца с пепперони и сыром'")
    elif query.data == "quick_photo_analysis":
        context.user_data['quick_analysis_mode'] = True
        await query.edit_message_text("📸 Отправьте мне фотографию еды для быстрого анализа калорий.\n\nРезультат не будет сохранен в дневной расчет.")
    elif query.data == "quick_text_analysis":
        context.user_data['quick_analysis_mode'] = True
        await query.edit_message_text("📝 Опишите еду текстом для быстрого анализа калорий.\n\nНапример: 'Большая пицца с пепперони и сыром'\n\nРезультат не будет сохранен в дневной расчет.")
    elif query.data == "quick_voice_analysis":
        context.user_data['quick_analysis_mode'] = True
        await query.edit_message_text("🎤 Отправьте мне голосовое сообщение с описанием еды для быстрого анализа калорий.\n\nНапример, скажите: 'Большая пицца с пепперони и сыром'\n\nРезультат не будет сохранен в дневной расчет.")
    elif query.data == "profile":
        await show_profile(query, context)
    elif query.data == "history":
        await show_calorie_history_menu(query, context)
    elif query.data == "history_today":
        await show_calorie_history(query, context, "today")
    elif query.data == "history_yesterday":
        await show_calorie_history(query, context, "yesterday")
    elif query.data == "history_week":
        await show_calorie_history(query, context, "week")
    elif query.data == "back_to_main":
        await show_main_menu(query, context)
    elif query.data == "add_food":
        await show_meal_type_menu(query, context)
    elif query.data == "quick_analysis":
        await show_quick_analysis_menu(query, context)
    elif query.data == "main_menu_submenu":
        await show_main_menu_submenu(query, context)
    elif query.data in ["meal_breakfast", "meal_lunch", "meal_dinner", "meal_snack"]:
        # Проверяем, нужно ли сбросить счетчик (новый день)
        await check_and_reset_daily_meals(context)
        
        # Сохраняем выбранный тип приема пищи в контекст
        meal_types = {
            "meal_breakfast": "🌅 Завтрак",
            "meal_lunch": "🍽️ Обед", 
            "meal_dinner": "🌙 Ужин",
            "meal_snack": "🍎 Перекус"
        }
        meal_keys = {
            "meal_breakfast": "breakfast",
            "meal_lunch": "lunch",
            "meal_dinner": "dinner",
            "meal_snack": "snack"
        }
        
        context.user_data['selected_meal_type'] = meal_types[query.data]
        
        # Добавляем выбранный тип приема пищи в список (кроме перекуса)
        if query.data != "meal_snack":
            if 'selected_meals_today' not in context.user_data:
                context.user_data['selected_meals_today'] = set()
            context.user_data['selected_meals_today'].add(meal_keys[query.data])
        
        await show_add_food_menu(query, context)
    elif query.data == "meal_type":
        await show_meal_type_menu(query, context)
    elif query.data.startswith("gender_"):
        await handle_gender_selection(query, context)
    elif query.data.startswith("activity_"):
        await handle_activity_selection(query, context)
    elif query.data == "edit_profile":
        await start_registration_flow(query, context)
    elif query.data == "confirm_reset":
        await confirm_reset(query, context)
    elif query.data == "cancel_reset":
        await cancel_reset(query, context)

async def start_registration_flow(query, context):
    """Начало процесса регистрации"""
    user_id = query.from_user.id
    
    # Сохраняем начальные данные пользователя
    user_data = {
        'user_id': user_id,
        'username': query.from_user.username,
        'first_name': query.from_user.first_name,
        'last_name': query.from_user.last_name
    }
    
    # Сохраняем в контексте для дальнейшего использования
    context.user_data['registration_data'] = user_data
    context.user_data['registration_step'] = 'name'
    
    await query.edit_message_text(
        "📝 Регистрация\n\n"
        "Введите ваше имя:"
    )

async def show_profile(query, context):
    """Показ профиля пользователя"""
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user:
        profile_text = f"👤 Ваш профиль:\n\n"
        profile_text += f"Имя: {user.get('name', 'Не указано')}\n"
        profile_text += f"Пол: {user.get('gender', 'Не указан')}\n"
        profile_text += f"Возраст: {user.get('age', 'Не указан')} лет\n"
        profile_text += f"Рост: {user.get('height', 'Не указан')} см\n"
        profile_text += f"Вес: {user.get('weight', 'Не указан')} кг\n"
        # Форматируем уровень активности для лучшего отображения
        activity_display = {
            'сидячая работа': '🏢 Сидячая работа (офис, учеба)',
            'легкая активность': '🚶 Легкая активность (прогулки, домашние дела)',
            'умеренная активность': '🏃 Умеренная активность (спорт 3-5 раз/неделю)',
            'высокая активность': '💪 Высокая активность (спорт 6-7 раз/неделю)',
            'физическая работа': '🏗️ Физическая работа (строительство, грузчик)'
        }
        activity_level = user.get('activity_level', 'Не указан')
        activity_text = activity_display.get(activity_level, activity_level)
        profile_text += f"Уровень активности: {activity_text}\n"
        daily_calories = user.get('daily_calories', 'Не рассчитана')
        if daily_calories != 'Не рассчитана':
            profile_text += f"Суточная норма калорий: **{daily_calories} ккал**\n\n"
            profile_text += "📊 **Расчет основан на:**\n"
            profile_text += f"• Формула Миффлина-Сан Жеора\n"
            profile_text += f"• Ваш уровень активности\n"
        else:
            profile_text += f"Суточная норма калорий: {daily_calories}"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать профиль", callback_data="edit_profile")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ Профиль не найден. Начните регистрацию заново.")

async def show_calorie_history_menu(query, context):
    """Показ меню истории калорий"""
    keyboard = [
        [InlineKeyboardButton("📅 Сегодня", callback_data="history_today")],
        [InlineKeyboardButton("📅 Вчера", callback_data="history_yesterday")],
        [InlineKeyboardButton("📅 За неделю", callback_data="history_week")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📊 **История калорий**\n\n"
        "Выберите период для просмотра:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_calorie_history(query, context, period="today"):
    """Показ истории калорий за выбранный период"""
    user_id = query.from_user.id
    from datetime import datetime, date, timedelta
    
    # Определяем даты в зависимости от периода
    today = date.today()
    if period == "today":
        start_date = today
        end_date = today
        period_name = "сегодня"
    elif period == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
        period_name = "вчера"
    elif period == "week":
        start_date = today - timedelta(days=7)
        end_date = today
        period_name = "за неделю"
    else:
        start_date = today
        end_date = today
        period_name = "сегодня"
    
    # Получаем историю за период
    history = db.get_user_calorie_history_by_period(user_id, start_date, end_date)
    
    if history:
        total_calories = sum(record['calories'] for record in history)
        history_text = f"📊 **История калорий за {period_name}**\n\n"
        history_text += f"**Общее количество калорий: {total_calories} ккал**\n\n"
        
        if period == "week":
            # Для недели группируем по дням
            from collections import defaultdict
            daily_calories = defaultdict(int)
            daily_names = {
                0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг",
                4: "Пятница", 5: "Суббота", 6: "Воскресенье"
            }
            
            for record in history:
                try:
                    # Парсим дату
                    created_at = record['created_at']
                    if 'T' in created_at:
                        record_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        record_datetime = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    
                    # Группируем по дням недели
                    day_of_week = record_datetime.weekday()
                    daily_calories[day_of_week] += record['calories']
                except:
                    # Если не удается распарсить дату, пропускаем запись
                    continue
            
            # Показываем калории по дням недели
            for day_num in range(7):
                day_name = daily_names[day_num]
                calories = daily_calories.get(day_num, 0)
                if calories > 0:
                    history_text += f"📅 **{day_name}**: {calories} ккал\n"
                else:
                    history_text += f"📅 **{day_name}**: 0 ккал\n"
        else:
            # Для сегодня и вчера показываем детальный список
            for record in history:
                # Форматируем дату и время
                try:
                    # Пробуем разные форматы даты
                    created_at = record['created_at']
                    if 'T' in created_at:
                        # ISO формат
                        record_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        # SQLite формат
                        record_datetime = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    formatted_time = record_datetime.strftime("%H:%M")
                except:
                    # Если не удается распарсить дату, показываем как есть
                    formatted_time = record['created_at'].split(' ')[-1][:5] if ' ' in record['created_at'] else record['created_at']
                
                history_text += f"• {record['food_description']}: {record['calories']} ккал\n"
                history_text += f"  Тип: {record['analysis_type']} | {formatted_time}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Выбрать другой период", callback_data="history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(history_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        keyboard = [
            [InlineKeyboardButton("📊 Выбрать другой период", callback_data="history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **История калорий за {period_name}**\n\n"
            f"За этот период записей не найдено.\n\n"
            f"Начните анализировать еду, чтобы увидеть историю!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def show_main_menu(query, context):
    """Показ главного меню для зарегистрированных пользователей"""
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    # Проверяем, нужно ли сбросить счетчик (новый день)
    await check_and_reset_daily_meals(context)
    
    if user:
        keyboard = [
            [InlineKeyboardButton("🍽️ Добавить блюдо", callback_data="add_food")],
            [InlineKeyboardButton("🔍 Хочу знать сколько калорий", callback_data="quick_analysis")],
            [InlineKeyboardButton("📋 Меню", callback_data="main_menu_submenu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        daily_calories = user.get('daily_calories', 0)
        await query.edit_message_text(
            f"🍕 Привет, {user.get('name', 'пользователь')}!\n\n"
            f"Ваша суточная норма калорий: {daily_calories} ккал\n\n"
            f"Выберите способ анализа:",
            reply_markup=reply_markup
        )
    else:
        await start_registration(query, context)

async def show_analysis_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ меню для нового анализа после ответа"""
    keyboard = [
        [InlineKeyboardButton("🍽️ Добавить блюдо", callback_data="add_food")],
        [InlineKeyboardButton("🔍 Хочу знать сколько калорий", callback_data="quick_analysis")],
        [InlineKeyboardButton("📋 Меню", callback_data="main_menu_submenu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔄 Хотите проанализировать что-то еще?",
        reply_markup=reply_markup
    )

async def check_and_reset_daily_meals(context):
    """Проверяет и сбрасывает счетчик выбранных приемов пищи и общую сумму калорий в полночь"""
    from datetime import datetime, date
    
    current_date = date.today()
    last_reset_date = context.user_data.get('last_reset_date')
    
    # Если это новый день, сбрасываем счетчик
    if last_reset_date != current_date:
        context.user_data['selected_meals_today'] = set()
        context.user_data['last_reset_date'] = current_date
        # Сбрасываем общую сумму калорий за день
        context.user_data['daily_calories_sum'] = 0
        logger.info(f"Daily meals reset for new day: {current_date}")

# Удаляем сложные функции планировщика - используем простую логику проверки при каждом взаимодействии

def get_daily_calories_sum(user_id):
    """Получает общую сумму калорий за сегодня"""
    from datetime import date, datetime
    
    today = date.today()
    history = db.get_user_calorie_history(user_id, limit=100)  # Получаем больше записей
    
    daily_sum = 0
    for record in history:
        # Проверяем, что запись за сегодня
        record_date = datetime.fromisoformat(record['created_at']).date()
        if record_date == today:
            daily_sum += record['calories']
    
    return daily_sum

async def show_meal_type_menu(query, context):
    """Показать меню выбора типа приема пищи"""
    user_id = query.from_user.id
    
    # Проверяем, нужно ли сбросить счетчик (новый день)
    await check_and_reset_daily_meals(context)
    
    # Получаем уже выбранные типы приема пищи за сегодня
    selected_meals = context.user_data.get('selected_meals_today', set())
    
    # Создаем кнопки только для не выбранных типов приема пищи
    keyboard = []
    
    if "breakfast" not in selected_meals:
        keyboard.append([InlineKeyboardButton("🌅 Завтрак", callback_data="meal_breakfast")])
    if "lunch" not in selected_meals:
        keyboard.append([InlineKeyboardButton("🍽️ Обед", callback_data="meal_lunch")])
    if "dinner" not in selected_meals:
        keyboard.append([InlineKeyboardButton("🌙 Ужин", callback_data="meal_dinner")])
    
    # Перекус всегда доступен
    keyboard.append([InlineKeyboardButton("🍎 Перекус", callback_data="meal_snack")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем сообщение с информацией о выбранных приемах пищи
    selected_text = ""
    if selected_meals:
        meal_names = []
        if "breakfast" in selected_meals:
            meal_names.append("🌅 Завтрак")
        if "lunch" in selected_meals:
            meal_names.append("🍽️ Обед")
        if "dinner" in selected_meals:
            meal_names.append("🌙 Ужин")
        selected_text = f"\n\n✅ Уже добавлено сегодня: {', '.join(meal_names)}"
    
    await query.edit_message_text(
        f"🍽️ **Добавить блюдо**\n\n"
        f"Выберите тип приема пищи:{selected_text}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_main_menu_submenu(query, context):
    """Показ подменю главного меню"""
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 История калорий", callback_data="history")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 **Меню**\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_quick_analysis_menu(query, context):
    """Показ меню быстрого анализа калорий (без сохранения в дневной расчет)"""
    keyboard = [
        [InlineKeyboardButton("📸 По фотографии", callback_data="quick_photo_analysis")],
        [InlineKeyboardButton("📝 По описанию", callback_data="quick_text_analysis")],
        [InlineKeyboardButton("🎤 По голосовому сообщению", callback_data="quick_voice_analysis")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔍 **Быстрый анализ калорий**\n\n"
        "Выберите способ анализа. Результат не будет сохранен в дневной расчет:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_add_food_menu(query, context):
    """Показ подменю для добавления блюда"""
    keyboard = [
        [InlineKeyboardButton("📸 По фотографии", callback_data="photo_analysis")],
        [InlineKeyboardButton("📝 По описанию", callback_data="text_analysis")],
        [InlineKeyboardButton("🎤 По голосовому сообщению", callback_data="voice_analysis")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="meal_type")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🍽️ Выберите способ добавления блюда:",
        reply_markup=reply_markup
    )

async def handle_gender_selection(query, context):
    """Обработка выбора пола"""
    gender = "мужской" if query.data == "gender_male" else "женский"
    context.user_data['registration_data']['gender'] = gender
    context.user_data['registration_step'] = 'age'
    
    await query.edit_message_text("Введите ваш возраст:")

async def handle_activity_selection(query, context):
    """Обработка выбора уровня активности"""
    activity_map = {
        "activity_sedentary": "сидячая работа",
        "activity_light": "легкая активность", 
        "activity_moderate": "умеренная активность",
        "activity_high": "высокая активность",
        "activity_very_high": "физическая работа"
    }
    
    activity_level = activity_map.get(query.data, "умеренная активность")
    context.user_data['registration_data']['activity_level'] = activity_level
    context.user_data['registration_data']['workouts_per_week'] = 0  # Устанавливаем 0 по умолчанию
    context.user_data['registration_step'] = 'complete'
    
    # Завершаем регистрацию
    user_data = context.user_data['registration_data']
    await complete_registration(query, context, user_data)

async def handle_quick_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фотографий для быстрого анализа (без сохранения в дневной расчет)"""
    try:
        user_id = update.effective_user.id
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Получаем информацию о фотографии
        photo = update.message.photo[-1]  # Берем фото в наилучшем качестве
        
        # Скачиваем изображение
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
        
        # Отправляем сообщение о начале анализа
        await update.message.reply_text("🔍 Анализирую изображение для быстрого анализа...")
        
        # Анализируем изображение
        result = analyze_food_image(image_data)
        
        # Отправляем результат без сохранения в историю
        await update.message.reply_text(f"🔍 **Быстрый анализ калорий**\n\n{result}\n\n💡 Результат не сохранен в дневной расчет", parse_mode='Markdown')
        
        # Показываем меню для следующего действия
        await show_analysis_menu(update, context)
        
    except Exception as e:
        logging.error(f"Error in quick photo analysis: {e}")
        await update.message.reply_text("❌ Извините, не удалось проанализировать изображение. Попробуйте еще раз.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фотографий"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        logger.info(f"User {user_id} ({username}) sent photo for analysis")
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            logger.warning(f"Unregistered user {user_id} tried to analyze photo")
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Проверяем режим быстрого анализа
        if context.user_data.get('quick_analysis_mode'):
            context.user_data['quick_analysis_mode'] = False  # Сбрасываем флаг
            logger.info(f"User {user_id} using quick analysis mode for photo")
            await handle_quick_photo(update, context)
            return
        
        # Получаем информацию о фотографии
        photo = update.message.photo[-1]  # Берем фото в наилучшем качестве
        
        # Скачиваем изображение
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
        
        # Получаем выбранный тип приема пищи
        meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
        logger.info(f"Analyzing photo for {meal_type} for user {user_id}")
        
        # Отправляем сообщение о начале анализа
        await update.message.reply_text(f"Анализирую изображение для {meal_type}...")
        
        # Анализируем изображение
        result = analyze_food_image(image_data)
        
        # Извлекаем количество калорий из результата
        calories = extract_calories_from_text(result)
        if calories:
            # Получаем выбранный тип приема пищи
            meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
            # Сохраняем в историю
            db.add_calorie_record(user_id, f"{meal_type} - Фотография еды", calories, "photo")
            logger.info(f"Saved photo analysis: {calories} calories for user {user_id}")
            
            # Получаем общую сумму калорий за сегодня
            daily_sum = get_daily_calories_sum(user_id)
            daily_calories = user.get('daily_calories', 0)
            
            # Формируем ответ
            result = format_calorie_response(calories, daily_sum, daily_calories)
        else:
            logger.warning(f"Could not extract calories from photo analysis result: {result}")
        
        # Отправляем результат
        await update.message.reply_text(result)
        
        # Показываем меню для нового запроса
        await show_analysis_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error handling photo for user {user_id}: {e}")
        await update.message.reply_text("Произошла ошибка при обработке фотографии. Попробуйте еще раз.")

async def handle_quick_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений для быстрого анализа (без сохранения в дневной расчет)"""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        # Проверяем, идет ли процесс регистрации
        if 'registration_step' in context.user_data:
            await handle_registration_text(update, context, text)
            return
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Отправляем сообщение о начале анализа
        await update.message.reply_text("🔍 Анализирую описание для быстрого анализа...")
        
        # Анализируем текст
        result = analyze_food_text(text)
        
        # Отправляем результат без сохранения в историю
        await update.message.reply_text(f"🔍 **Быстрый анализ калорий**\n\n{result}\n\n💡 Результат не сохранен в дневной расчет", parse_mode='Markdown')
        
        # Показываем меню для следующего действия
        await show_analysis_menu(update, context)
        
    except Exception as e:
        logging.error(f"Error in quick text analysis: {e}")
        await update.message.reply_text("❌ Извините, не удалось проанализировать описание. Попробуйте еще раз.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        # Проверяем, идет ли процесс регистрации
        if 'registration_step' in context.user_data:
            await handle_registration_text(update, context, text)
            return
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Проверяем режим быстрого анализа
        if context.user_data.get('quick_analysis_mode'):
            context.user_data['quick_analysis_mode'] = False  # Сбрасываем флаг
            await handle_quick_text(update, context)
            return
        
        # Получаем выбранный тип приема пищи
        meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
        # Отправляем сообщение о начале анализа
        await update.message.reply_text(f"Анализирую описание для {meal_type}...")
        
        # Анализируем текст
        result = analyze_food_text(text)
        
        # Извлекаем количество калорий из результата
        calories = extract_calories_from_text(result)
        if calories:
            # Получаем выбранный тип приема пищи
            meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
            # Сохраняем в историю
            db.add_calorie_record(user_id, f"{meal_type} - {text}", calories, "text")
            
            # Получаем общую сумму калорий за сегодня
            daily_sum = get_daily_calories_sum(user_id)
            daily_calories = user.get('daily_calories', 0)
            
            # Формируем ответ
            result = format_calorie_response(calories, daily_sum, daily_calories)
        else:
            logger.warning(f"Could not extract calories from result: {result}")
        
        # Отправляем результат
        await update.message.reply_text(result)
        
        # Показываем меню для нового запроса
        await show_analysis_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("Произошла ошибка при обработке текста. Попробуйте еще раз.")

async def handle_registration_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка текста во время регистрации"""
    step = context.user_data.get('registration_step')
    user_data = context.user_data.get('registration_data', {})
    
    if step == 'name':
        user_data['name'] = text
        context.user_data['registration_step'] = 'gender'
        
        keyboard = [
            [InlineKeyboardButton("Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("Женский", callback_data="gender_female")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Приятно познакомиться, {text}!\n\n"
            "Выберите ваш пол:",
            reply_markup=reply_markup
        )
    
    elif step == 'age':
        age = validate_user_input(text, "age")
        if age is not None:
            user_data['age'] = age
            context.user_data['registration_step'] = 'height'
            await update.message.reply_text("Введите ваш рост в сантиметрах:")
        else:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (10-120 лет):")
    
    elif step == 'height':
        height = validate_user_input(text, "height")
        if height is not None:
            user_data['height'] = height
            context.user_data['registration_step'] = 'weight'
            await update.message.reply_text("Введите ваш вес в килограммах:")
        else:
            await update.message.reply_text("Пожалуйста, введите корректный рост (100-250 см):")
    
    elif step == 'weight':
        weight = validate_user_input(text, "weight")
        if weight is not None:
            user_data['weight'] = weight
            context.user_data['registration_step'] = 'activity'
            
            keyboard = [
                [InlineKeyboardButton("🏢 Сидячая работа (офис, учеба)", callback_data="activity_sedentary")],
                [InlineKeyboardButton("🚶 Легкая активность (прогулки, домашние дела)", callback_data="activity_light")],
                [InlineKeyboardButton("🏃 Умеренная активность (спорт 3-5 раз/неделю)", callback_data="activity_moderate")],
                [InlineKeyboardButton("💪 Высокая активность (спорт 6-7 раз/неделю)", callback_data="activity_high")],
                [InlineKeyboardButton("🏗️ Физическая работа (строительство, грузчик)", callback_data="activity_very_high")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🏃‍♂️ **Выберите уровень вашей физической активности:**\n\n"
                "Это поможет точно рассчитать вашу суточную норму калорий.\n"
                "Выберите тот вариант, который лучше всего описывает ваш образ жизни:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("Пожалуйста, введите корректный вес (30-300 кг):")
    

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Завершение регистрации"""
    try:
        # Рассчитываем суточные калории
        daily_calories = db.calculate_daily_calories(
            user_data.get('gender'),
            user_data.get('age'),
            user_data.get('height'),
            user_data.get('weight'),
            user_data.get('activity_level')
        )
        user_data['daily_calories'] = daily_calories
        
        # Сохраняем пользователя в базу данных
        if db.add_user(user_data):
            # Очищаем данные регистрации
            context.user_data.pop('registration_step', None)
            context.user_data.pop('registration_data', None)
            
            keyboard = [
                [InlineKeyboardButton("🍕 Начать анализ еды", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎉 Регистрация завершена!\n\n"
                f"Ваша суточная норма калорий: {daily_calories} ккал\n\n"
                f"Теперь я смогу сравнивать калории в еде с вашей нормой!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при сохранении данных. Попробуйте еще раз.")
    
    except Exception as e:
        logger.error(f"Error completing registration: {e}")
        await update.message.reply_text("❌ Произошла ошибка при завершении регистрации. Попробуйте еще раз.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /reset"""
    user_id = update.effective_user.id
    
    # Создаем кнопки подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, сбросить все данные", callback_data="confirm_reset")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ ВНИМАНИЕ!\n\n"
        "Вы собираетесь удалить ВСЕ ваши данные:\n"
        "• Профиль и регистрационные данные\n"
        "• Всю историю калорий\n"
        "• Настройки и предпочтения\n\n"
        "Это действие НЕЛЬЗЯ отменить!\n\n"
        "Вы уверены, что хотите продолжить?",
        reply_markup=reply_markup
    )

async def dayres_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /dayres - сброс дневных данных"""
    user_id = update.effective_user.id
    
    # Проверяем, зарегистрирован ли пользователь
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
        return
    
    # Сбрасываем дневные данные пользователя
    context.user_data['selected_meals_today'] = set()
    context.user_data['daily_calories_sum'] = 0
    context.user_data['last_reset_date'] = None  # Сбрасываем дату, чтобы при следующем взаимодействии снова сработал сброс
    
    # Сбрасываем калории за сегодняшний день в базе данных
    success = db.reset_daily_calories(user_id)
    
    # Получаем текущую дату для логирования
    from datetime import date
    current_date = date.today()
    
    logger.info(f"Daily reset for user {user_id} on {current_date}")
    
    # Создаем кнопки для возврата в меню
    keyboard = [
        [InlineKeyboardButton("🍽️ Добавить блюдо", callback_data="add_food")],
        [InlineKeyboardButton("🔍 Быстрый анализ", callback_data="quick_analysis")],
        [InlineKeyboardButton("📋 Меню", callback_data="main_menu_submenu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if success:
        await update.message.reply_text(
            "✅ **Дневные данные сброшены!**\n\n"
            "🔄 Что было сброшено:\n"
            "• Выбранные приемы пищи (завтрак, обед, ужин)\n"
            "• Все записи калорий за сегодняшний день\n"
            "• Счетчик калорий за день\n\n"
            "Теперь вы можете заново добавить завтрак, обед и ужин!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ **Частичный сброс выполнен!**\n\n"
            "✅ Сброшены:\n"
            "• Выбранные приемы пищи (завтрак, обед, ужин)\n"
            "• Счетчик калорий за день\n\n"
            "❌ Не удалось сбросить записи калорий из базы данных.\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def confirm_reset(query, context):
    """Подтверждение сброса данных"""
    user_id = query.from_user.id
    
    try:
        # Сбрасываем все данные пользователя
        if db.reset_user_data(user_id):
            # Очищаем данные регистрации из контекста
            context.user_data.clear()
            
            keyboard = [
                [InlineKeyboardButton("🔄 Начать заново", callback_data="start_registration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Все данные успешно удалены!\n\n"
                "Ваш профиль, история калорий и все настройки были сброшены.\n\n"
                "Нажмите кнопку ниже, чтобы начать регистрацию заново:",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при удалении данных. Попробуйте еще раз позже."
            )
    
    except Exception as e:
        logger.error(f"Error confirming reset: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при сбросе данных. Попробуйте еще раз."
        )

async def cancel_reset(query, context):
    """Отмена сброса данных"""
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user:
        # Возвращаемся в главное меню
        await show_main_menu(query, context)
    else:
        # Если пользователь не зарегистрирован, показываем приветствие
        await start_registration(query, context)

async def handle_quick_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик голосовых сообщений для быстрого анализа (без сохранения в дневной расчет)"""
    try:
        user_id = update.effective_user.id
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Получаем информацию о голосовом сообщении
        voice = update.message.voice
        
        # Скачиваем аудио
        file = await context.bot.get_file(voice.file_id)
        audio_data = await file.download_as_bytearray()
        
        # Отправляем сообщение о начале обработки
        await update.message.reply_text("🔍 Обрабатываю голосовое сообщение для быстрого анализа...")
        
        # Транскрибируем голос в текст
        text = transcribe_voice(audio_data)
        
        if text:
            await update.message.reply_text(f"Распознанный текст: {text}")
            await update.message.reply_text("🔍 Анализирую описание для быстрого анализа...")
            
            # Анализируем текст
            result = analyze_food_text(text)
            
            # Отправляем результат без сохранения в историю
            await update.message.reply_text(f"🔍 **Быстрый анализ калорий**\n\n{result}\n\n💡 Результат не сохранен в дневной расчет", parse_mode='Markdown')
            
            # Показываем меню для следующего действия
            await show_analysis_menu(update, context)
        else:
            await update.message.reply_text("❌ Не удалось распознать речь. Попробуйте еще раз.")
            
    except Exception as e:
        logging.error(f"Error in quick voice analysis: {e}")
        await update.message.reply_text("❌ Извините, не удалось обработать голосовое сообщение. Попробуйте еще раз.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик голосовых сообщений"""
    try:
        user_id = update.effective_user.id
        
        # Проверяем, зарегистрирован ли пользователь
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Сначала пройдите регистрацию командой /start")
            return
        
        # Проверяем режим быстрого анализа
        if context.user_data.get('quick_analysis_mode'):
            context.user_data['quick_analysis_mode'] = False  # Сбрасываем флаг
            await handle_quick_voice(update, context)
            return
        
        # Получаем информацию о голосовом сообщении
        voice = update.message.voice
        
        # Скачиваем аудио
        file = await context.bot.get_file(voice.file_id)
        audio_data = await file.download_as_bytearray()
        
        # Отправляем сообщение о начале обработки
        await update.message.reply_text("Обрабатываю голосовое сообщение...")
        
        # Транскрибируем голос в текст
        text = transcribe_voice(audio_data)
        
        if text:
            await update.message.reply_text(f"Распознанный текст: {text}")
            # Получаем выбранный тип приема пищи
            meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
            await update.message.reply_text(f"Анализирую описание для {meal_type}...")
            
            # Анализируем текст
            result = analyze_food_text(text)
            
            # Извлекаем количество калорий из результата
            calories = extract_calories_from_text(result)
            if calories:
                # Получаем выбранный тип приема пищи
                meal_type = context.user_data.get('selected_meal_type', '🍽️ Блюдо')
                # Сохраняем в историю
                db.add_calorie_record(user_id, f"{meal_type} - {text}", calories, "voice")
                
                # Получаем общую сумму калорий за сегодня
                daily_sum = get_daily_calories_sum(user_id)
                daily_calories = user.get('daily_calories', 0)
                
                # Формируем ответ
                result = format_calorie_response(calories, daily_sum, daily_calories)
            else:
                logger.warning(f"Could not extract calories from result: {result}")
            
            # Отправляем результат
            await update.message.reply_text(result)
            
            # Показываем меню для нового запроса
            await show_analysis_menu(update, context)
        else:
            await update.message.reply_text("Не удалось распознать речь. Попробуйте еще раз или используйте текстовое описание.")
        
    except Exception as e:
        logger.error(f"Error handling voice: {e}")
        await update.message.reply_text("Произошла ошибка при обработке голосового сообщения. Попробуйте еще раз.")

async def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("dayres", dayres_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Запускаем бота
    print("Бот запущен...")
    print("Автоматический сброс приемов пищи при первом взаимодействии нового дня")
    await application.run_polling()

if __name__ == '__main__':
    try:
        # Попробуем запустить с asyncio.run()
        asyncio.run(main())
    except RuntimeError as e:
        if "This event loop is already running" in str(e) or "Cannot close a running event loop" in str(e):
            # Если event loop уже запущен, используем другой подход
            try:
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(main())
            except ImportError:
                # Если nest_asyncio не установлен, используем альтернативный метод
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Создаем новую задачу в существующем loop
                    loop.create_task(main())
                else:
                    loop.run_until_complete(main())
        else:
            raise e
