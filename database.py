import sqlite3
import logging
import os
import threading
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class UserDatabase:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.use_postgres = os.getenv('DATABASE_URL') is not None
        self._lock = threading.Lock()
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager для безопасной работы с базой данных"""
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Для удобного доступа к колонкам
            try:
                yield conn
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        name TEXT,
                        gender TEXT,
                        age INTEGER,
                        height REAL,
                        weight REAL,
                        activity_level TEXT,
                        workout_types TEXT,
                        daily_calories INTEGER,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Создаем таблицу истории калорий
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS calorie_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        food_description TEXT,
                        calories INTEGER,
                        analysis_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Создаем индексы для оптимизации запросов
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_calorie_history_user_id 
                    ON calorie_history(user_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_calorie_history_created_at 
                    ON calorie_history(created_at)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_calorie_history_user_date 
                    ON calorie_history(user_id, DATE(created_at))
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_user(self, user_data: Dict[str, Any]) -> bool:
        """Добавление нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, name, gender, age, height, weight, 
                     activity_level, workout_types, daily_calories)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('name'),
                    user_data.get('gender'),
                    user_data.get('age'),
                    user_data.get('height'),
                    user_data.get('weight'),
                    user_data.get('activity_level'),
                    user_data.get('workout_types'),
                    user_data.get('daily_calories')
                ))
                
                conn.commit()
                logger.info(f"User {user_data['user_id']} added/updated successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM users WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_field(self, user_id: int, field: str, value: Any) -> bool:
        """Обновление конкретного поля пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    UPDATE users SET {field} = ? WHERE user_id = ?
                ''', (value, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating user field: {e}")
            return False
    
    def add_calorie_record(self, user_id: int, food_description: str, calories: int, analysis_type: str) -> bool:
        """Добавление записи о калориях"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO calorie_history (user_id, food_description, calories, analysis_type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, food_description, calories, analysis_type))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding calorie record: {e}")
            return False
    
    def get_user_calorie_history(self, user_id: int, limit: int = 10) -> list:
        """Получение истории калорий пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calorie_history 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting calorie history: {e}")
            return []
    
    def get_user_calorie_history_by_period(self, user_id: int, start_date, end_date) -> list:
        """Получение истории калорий пользователя за определенный период"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calorie_history 
                    WHERE user_id = ? 
                    AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                ''', (user_id, start_date, end_date))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting calorie history by period: {e}")
            return []
    
    def calculate_daily_calories(self, gender: str, age: int, height: float, weight: float, 
                                activity_level: str) -> int:
        """Расчет суточных калорий по формуле Миффлина-Сан Жеора"""
        try:
            # Базовый метаболизм (BMR)
            if gender.lower() == 'мужской':
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
            
            # Коэффициент активности (формула Миффлина-Сан Жеора)
            activity_multipliers = {
                'сидячая работа': 1.2,           # Сидячий образ жизни, офисная работа
                'легкая активность': 1.375,      # Легкие упражнения 1-3 раза в неделю
                'умеренная активность': 1.55,    # Умеренные упражнения 3-5 раз в неделю
                'высокая активность': 1.725,     # Интенсивные упражнения 6-7 раз в неделю
                'физическая работа': 1.9         # Очень интенсивные упражнения, физическая работа
            }
            
            multiplier = activity_multipliers.get(activity_level.lower(), 1.2)
            
            daily_calories = int(bmr * multiplier)
            return daily_calories
            
        except Exception as e:
            logger.error(f"Error calculating daily calories: {e}")
            return 2000  # Значение по умолчанию
    
    def reset_user_data(self, user_id: int) -> bool:
        """Полный сброс данных пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем историю калорий
                cursor.execute('''
                    DELETE FROM calorie_history WHERE user_id = ?
                ''', (user_id,))
                
                # Удаляем данные пользователя
                cursor.execute('''
                    DELETE FROM users WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                logger.info(f"User {user_id} data reset successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting user data: {e}")
            return False
    
    def reset_daily_calories(self, user_id: int) -> bool:
        """Сброс калорий за сегодняшний день"""
        try:
            from datetime import date
            
            today = date.today()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем записи калорий за сегодня
                cursor.execute('''
                    DELETE FROM calorie_history 
                    WHERE user_id = ? AND DATE(created_at) = ?
                ''', (user_id, today))
                
                conn.commit()
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} calorie records for user {user_id} on {today}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting daily calories: {e}")
            return False
