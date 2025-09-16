#!/usr/bin/env python3
"""
Скрипт для очистки базы данных на Railway
Используется когда проект развернут на сервере
"""
import os
import sys

def clear_railway_database():
    """Очистка базы данных на Railway через API или прямые команды"""
    print("🌐 Очистка базы данных на Railway...")
    
    # Проверяем переменные окружения Railway
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не найден")
        print("Убедитесь, что вы находитесь в среде Railway или установите переменную")
        return False
    
    print(f"📊 Подключение к базе: {database_url[:20]}...")
    
    try:
        from database import UserDatabase
        
        db = UserDatabase()
        
        # Получаем статистику
        stats = db.get_database_stats()
        print(f"Пользователей: {stats.get('users_count', 0)}")
        print(f"Записей калорий: {stats.get('records_count', 0)}")
        
        # Очищаем все данные
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем записи калорий
            cursor.execute("DELETE FROM calorie_history;")
            deleted_calories = cursor.rowcount
            print(f"✅ Удалено записей калорий: {deleted_calories}")
            
            # Удаляем пользователей
            cursor.execute("DELETE FROM users;")
            deleted_users = cursor.rowcount
            print(f"✅ Удалено пользователей: {deleted_users}")
            
            # Сбрасываем последовательности для PostgreSQL
            if db.use_postgres:
                cursor.execute("ALTER SEQUENCE calorie_history_id_seq RESTART WITH 1;")
                print("✅ Последовательности сброшены")
            
            conn.commit()
        
        # Проверяем результат
        final_stats = db.get_database_stats()
        if final_stats.get('users_count', 0) == 0 and final_stats.get('records_count', 0) == 0:
            print("🎉 База данных на Railway полностью очищена!")
            return True
        else:
            print("⚠️ Некоторые данные могли остаться")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("🌐 Очистка базы данных на Railway")
    print("=" * 40)
    
    if clear_railway_database():
        print("\n✅ Очистка завершена успешно!")
    else:
        print("\n❌ Очистка завершилась с ошибками")
    
    print("=" * 40)

if __name__ == "__main__":
    main()
