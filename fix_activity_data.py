#!/usr/bin/env python3
"""
Скрипт для исправления неправильных данных активности в базе данных
"""
import sqlite3
import os

def fix_activity_data():
    """Исправляет неправильные данные активности в базе данных"""
    
    # Проверяем, существует ли база данных
    if not os.path.exists('users.db'):
        print("База данных users.db не найдена")
        return
    
    # Подключаемся к базе данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Словарь для исправления неправильных значений
    activity_fixes = {
        'activity_sedentary': 'сидячая работа',
        'activity_light': 'легкая активность',
        'activity_moderate': 'умеренная активность',
        'activity_high': 'высокая активность',
        'activity_very_high': 'физическая работа',
        'moderate': 'умеренная активность',
        'light': 'легкая активность',
        'sedentary': 'сидячая работа',
        'high': 'высокая активность',
        'very_high': 'физическая работа'
    }
    
    print("=== ИСПРАВЛЕНИЕ ДАННЫХ АКТИВНОСТИ ===\n")
    
    # Получаем всех пользователей
    cursor.execute('SELECT user_id, username, name, activity_level, daily_calories FROM users')
    users = cursor.fetchall()
    
    if not users:
        print("Пользователи не найдены в базе данных")
        conn.close()
        return
    
    print(f"Найдено пользователей: {len(users)}\n")
    
    fixes_applied = 0
    
    for user in users:
        user_id, username, name, activity_level, daily_calories = user
        
        print(f"Пользователь {user_id}: {name}")
        print(f"  Текущая активность: {repr(activity_level)}")
        
        # Проверяем, нужно ли исправить
        if activity_level in activity_fixes:
            new_activity = activity_fixes[activity_level]
            print(f"  ⚠️  Исправляем: {repr(activity_level)} → {repr(new_activity)}")
            
            # Пересчитываем калории
            new_daily_calories = recalculate_daily_calories(user_id, new_activity)
            
            # Обновляем данные в базе
            cursor.execute('''
                UPDATE users 
                SET activity_level = ?, daily_calories = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_activity, new_daily_calories, user_id))
            
            print(f"  ✅ Обновлено: {daily_calories} → {new_daily_calories} ккал")
            fixes_applied += 1
        else:
            print(f"  ✅ Данные корректные")
        
        print()
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    print(f"=== РЕЗУЛЬТАТ ===")
    print(f"Исправлено пользователей: {fixes_applied}")
    print(f"Всего пользователей: {len(users)}")

def recalculate_daily_calories(user_id, activity_level):
    """Пересчитывает суточную норму калорий для пользователя"""
    
    # Получаем данные пользователя
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT gender, age, height, weight FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data:
        return 2000  # Значение по умолчанию
    
    gender, age, height, weight = user_data
    
    # Расчет BMR
    if gender.lower() == 'мужской':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # женский
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Коэффициенты активности
    activity_multipliers = {
        'сидячая работа': 1.2,
        'легкая активность': 1.375,
        'умеренная активность': 1.55,
        'высокая активность': 1.725,
        'физическая работа': 1.9
    }
    
    multiplier = activity_multipliers.get(activity_level.lower(), 1.2)
    daily_calories = int(bmr * multiplier)
    
    return daily_calories

if __name__ == "__main__":
    fix_activity_data()
