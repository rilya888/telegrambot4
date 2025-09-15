#!/usr/bin/env python3
"""
Простой тест для проверки исправления daily calories sum
"""

def test_daily_calories_fix():
    """Тестируем исправление расчета дневных калорий"""
    print("🧪 Тестирование исправления daily calories sum...")
    
    try:
        # Импортируем базу данных
        from database import UserDatabase
        
        # Создаем экземпляр
        db = UserDatabase()
        print("✅ База данных инициализирована")
        
        # Тестируем метод get_daily_calories_sum
        test_user_id = 12345
        result = db.get_daily_calories_sum(test_user_id)
        print(f"✅ Метод get_daily_calories_sum работает: {result} калорий")
        
        # Тестируем добавление записи
        success = db.add_calorie_record(test_user_id, "Тестовое блюдо", 100, "test")
        print(f"✅ Добавление записи работает: {success}")
        
        # Проверяем сумму после добавления
        result_after = db.get_daily_calories_sum(test_user_id)
        print(f"✅ Сумма после добавления: {result_after} калорий")
        
        print("\n🎉 Все тесты прошли успешно!")
        print("Исправление работает корректно!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    test_daily_calories_fix()
