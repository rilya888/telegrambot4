"""
Оптимизированная база данных для Telegram бота анализа калорий
"""
import os
import logging
import threading
import sqlite3
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

class UserDatabase:
    """Оптимизированный класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.use_postgres = os.getenv('DATABASE_URL') is not None
        self._lock = threading.Lock()
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager для безопасной работы с базой данных"""
        with self._lock:
            if self.use_postgres:
                try:
                    import psycopg2
                    from urllib.parse import urlparse
                    
                    url = urlparse(os.getenv('DATABASE_URL'))
                    conn = psycopg2.connect(
                        database=url.path[1:],
                        user=url.username,
                        password=url.password,
                        host=url.hostname,
                        port=url.port,
                        connect_timeout=10
                    )
                    try:
                        yield conn
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        conn.close()
                except ImportError:
                    logger.warning("psycopg2 not available, falling back to SQLite")
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.row_factory = sqlite3.Row
                    try:
                        yield conn
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        conn.close()
            else:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                try:
                    yield conn
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()
    
    def init_database(self):
        """Инициализация базы данных с оптимизированной структурой"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    # PostgreSQL таблицы
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255),
                            name VARCHAR(255),
                            gender VARCHAR(10),
                            age INTEGER,
                            height REAL,
                            weight REAL,
                            activity_level VARCHAR(50),
                            daily_calories INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS calorie_history (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT,
                            food_name TEXT,
                            calories INTEGER,
                            source TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    ''')
                    
                    # Создаем индексы для оптимизации
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
                else:
                    # SQLite таблицы
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT,
                            name TEXT,
                            gender TEXT,
                            age INTEGER,
                            height REAL,
                            weight REAL,
                            activity_level TEXT,
                            daily_calories INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS calorie_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            food_name TEXT,
                            calories INTEGER,
                            source TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    ''')
                
                    # Создаем индексы для оптимизации
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
                
                # Очищаем поврежденные данные
                self.clean_corrupted_data()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_user(self, user_data: Dict[str, Any]) -> bool:
        """Добавление или обновление пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        INSERT INTO users (user_id, username, name, gender, 
                                        age, height, weight, activity_level, daily_calories)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            username = EXCLUDED.username,
                            name = EXCLUDED.name,
                            gender = EXCLUDED.gender,
                            age = EXCLUDED.age,
                            height = EXCLUDED.height,
                            weight = EXCLUDED.weight,
                            activity_level = EXCLUDED.activity_level,
                            daily_calories = EXCLUDED.daily_calories,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (
                        user_data['user_id'], user_data.get('username'), user_data.get('name'), 
                        user_data.get('gender'), user_data.get('age'), user_data.get('height'), 
                        user_data.get('weight'), user_data.get('activity_level'), user_data.get('daily_calories')
                    ))
                else:
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (user_id, username, name, gender, 
                                                    age, height, weight, activity_level, daily_calories)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_data['user_id'], user_data.get('username'), user_data.get('name'), 
                        user_data.get('gender'), user_data.get('age'), user_data.get('height'), 
                        user_data.get('weight'), user_data.get('activity_level'), user_data.get('daily_calories')
                    ))
                
                conn.commit()
                logger.info(f"User {user_data['user_id']} added/updated successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT * FROM users WHERE user_id = %s' if self.use_postgres else 'SELECT * FROM users WHERE user_id = ?', 
                    (user_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    if self.use_postgres:
                        columns = [desc[0] for desc in cursor.description]
                        return dict(zip(columns, row))
                    else:
                        return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def add_calorie_record(self, user_id: int, food_name: str, calories: int, source: str = "unknown") -> bool:
        """Добавление записи о калориях"""
        try:
            # Упрощаем данные для оптимизации
            max_food_name_length = 50
            if len(food_name) > max_food_name_length:
                food_name = food_name[:max_food_name_length-3] + "..."
            
            # Маппинг источников для краткости
            source_map = {
                "photo": "фото",
                "text": "текст", 
                "voice": "голос",
                "unknown": "другое"
            }
            source = source_map.get(source, "другое")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        INSERT INTO calorie_history (user_id, food_name, calories, source)
                        VALUES (%s, %s, %s, %s)
                    ''', (user_id, food_name, calories, source))
                else:
                    cursor.execute('''
                        INSERT INTO calorie_history (user_id, food_name, calories, source)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, food_name, calories, source))
                
                conn.commit()
                logger.info(f"Successfully added calorie record for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding calorie record: {e}")
            return False
    
    def get_user_calorie_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить историю калорий пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        SELECT * FROM calorie_history 
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    ''', (user_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM calorie_history 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (user_id, limit))
                
                records = cursor.fetchall()
                
                # Преобразуем в список словарей
                history = []
                for record in records:
                    if self.use_postgres:
                        columns = [desc[0] for desc in cursor.description]
                        history.append(dict(zip(columns, record)))
                    else:
                        history.append(dict(record))
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting calorie history: {e}")
            return []
    
    def get_user_calorie_history_by_period(self, user_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Получение истории калорий пользователя за определенный период"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        SELECT * FROM calorie_history
                        WHERE user_id = %s
                        AND DATE(created_at) >= %s 
                        AND DATE(created_at) <= %s
                        ORDER BY created_at DESC
                    ''', (user_id, start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT * FROM calorie_history 
                        WHERE user_id = ? 
                        AND DATE(created_at) >= ? 
                        AND DATE(created_at) <= ?
                        ORDER BY created_at DESC
                    ''', (user_id, start_date, end_date))
                
                records = cursor.fetchall()
                
                # Преобразуем в список словарей
                history = []
                for record in records:
                    if self.use_postgres:
                        columns = [desc[0] for desc in cursor.description]
                        history.append(dict(zip(columns, record)))
                    else:
                        history.append(dict(record))
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting calorie history by period: {e}")
            return []
    
    def get_weekly_calories_summary(self, user_id: int) -> Dict[str, Any]:
        """Получение недельной сводки калорий по дням"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        SELECT 
                            DATE(created_at) as date,
                            SUM(calories) as daily_total,
                            COUNT(*) as meals_count
                        FROM calorie_history 
                        WHERE user_id = %s 
                        AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                        GROUP BY DATE(created_at)
                        ORDER BY date DESC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT 
                            DATE(created_at) as date,
                            SUM(calories) as daily_total,
                            COUNT(*) as meals_count
                        FROM calorie_history 
                        WHERE user_id = ? 
                        AND created_at >= DATE('now', '-7 days')
                        GROUP BY DATE(created_at)
                        ORDER BY date DESC
                    ''', (user_id,))
                
                rows = cursor.fetchall()
                
                # Преобразуем в словарь
                daily_data = {}
                total_weekly = 0
                
                for row in rows:
                    date_str = str(row[0])
                    daily_total = row[1] or 0
                    meals_count = row[2] or 0
                    
                    daily_data[date_str] = {
                        'calories': daily_total,
                        'meals': meals_count
                    }
                    total_weekly += daily_total
                
                return {
                    'daily_data': daily_data,
                    'total_weekly': total_weekly,
                    'days_count': len(daily_data)
                }
                
        except Exception as e:
            logger.error(f"Error getting weekly calories summary: {e}")
            return {'daily_data': {}, 'total_weekly': 0, 'days_count': 0}
    
    def get_daily_calories_sum(self, user_id: int) -> int:
        """Получение суммы калорий за сегодня"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        SELECT COALESCE(SUM(calories), 0) FROM calorie_history 
                        WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT COALESCE(SUM(calories), 0) FROM calorie_history 
                        WHERE user_id = ? AND DATE(created_at) = DATE('now')
                    ''', (user_id,))
                
                result = cursor.fetchone()
                daily_sum = result[0] if result else 0
                logger.info(f"Daily calories sum for user {user_id}: {daily_sum}")
                return daily_sum
                
        except Exception as e:
            logger.error(f"Error getting daily calories sum: {e}")
            return 0
    
    def reset_daily_calories(self, user_id: int) -> bool:
        """Сброс калорий за сегодняшний день"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        DELETE FROM calorie_history 
                        WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        DELETE FROM calorie_history 
                        WHERE user_id = ? AND DATE(created_at) = DATE('now')
                    ''', (user_id,))
                
                conn.commit()
                logger.info(f"Daily calories reset for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting daily calories: {e}")
            return False
    
    def reset_user_data(self, user_id: int) -> bool:
        """Полный сброс данных пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем историю калорий
                if self.use_postgres:
                    cursor.execute('DELETE FROM calorie_history WHERE user_id = %s', (user_id,))
                    cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
                else:
                    cursor.execute('DELETE FROM calorie_history WHERE user_id = ?', (user_id,))
                    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                
                conn.commit()
                logger.info(f"User {user_id} data reset successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting user data: {e}")
            return False
    
    def clean_corrupted_data(self) -> bool:
        """Очистка поврежденных данных в базе"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    # Для PostgreSQL удаляем записи где calories не является числом
                    cursor.execute('''
                        DELETE FROM calorie_history 
                        WHERE NOT (calories::text ~ '^[0-9]+$' AND calories > 0)
                    ''')
                else:
                    # Для SQLite используем GLOB
                    cursor.execute('''
                        DELETE FROM calorie_history 
                        WHERE calories NOT GLOB '[0-9]*' OR calories <= 0
                    ''')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned {deleted_count} corrupted calorie records")
                
                return True
                
        except Exception as e:
            logger.error(f"Error cleaning corrupted data: {e}")
            return False
    
    def calculate_daily_calories(self, gender: str, age: int, height: float, weight: float, 
                                activity_level: str) -> int:
        """Расчет суточной нормы калорий по формуле Миффлина-Сан Жеора"""
        try:
            # Базовый метаболизм (BMR) по формуле Миффлина-Сан Жеора
            if gender.lower() == 'мужской':
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:  # женский
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
            
            # Коэффициенты активности (обновленные значения)
            activity_multipliers = {
                'сидячая работа': 1.2,
                'легкая активность': 1.375,
                'умеренная активность': 1.55,
                'высокая активность': 1.725,
                'физическая работа': 1.9
            }
            
            logger.info(f"Calculate daily calories - activity_level: {repr(activity_level)}")
            logger.info(f"Calculate daily calories - activity_level.lower(): {repr(activity_level.lower())}")
            logger.info(f"Calculate daily calories - activity_multipliers: {activity_multipliers}")
            
            multiplier = activity_multipliers.get(activity_level.lower(), 1.2)
            
            logger.info(f"Calculate daily calories - selected multiplier: {multiplier}")
            logger.info(f"Calculate daily calories - BMR: {bmr:.2f}")
            
            daily_calories = int(bmr * multiplier)
            
            logger.info(f"Calculate daily calories - final result: {daily_calories} for {gender}, age {age}, height {height}, weight {weight}, activity {activity_level}")
            return daily_calories
            
        except Exception as e:
            logger.error(f"Error calculating daily calories: {e}")
            return 2000  # Значение по умолчанию
