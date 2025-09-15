import os
import logging
from typing import Optional, Dict, Any
import sqlite3

logger = logging.getLogger(__name__)

class UserDatabase:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.use_postgres = os.getenv('DATABASE_URL') is not None
        self.init_database()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
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
                    port=url.port
                )
                return conn
            except ImportError:
                logger.warning("psycopg2 not available, falling back to SQLite")
                return sqlite3.connect(self.db_path)
        else:
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                # PostgreSQL таблицы
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
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
            else:
                # SQLite таблицы
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
            
            conn.commit()
            conn.close()
            
            # Очищаем поврежденные данные
            self.clean_corrupted_data()
            
            logger.info("Database initialized successfully")
            
            # Проверяем и обновляем структуру таблицы calorie_history
            self.migrate_calorie_history_table()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def migrate_calorie_history_table(self):
        """Миграция таблицы calorie_history для обновления структуры"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                # Проверяем, существует ли колонка food_name
                cursor.execute('''
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'calorie_history' AND column_name = 'food_name'
                ''')
                
                if not cursor.fetchone():
                    logger.info("Migrating calorie_history table structure...")
                    # Переименовываем старые колонки в новые
                    cursor.execute('ALTER TABLE calorie_history RENAME COLUMN meal_type TO food_name')
                    cursor.execute('ALTER TABLE calorie_history RENAME COLUMN description TO source')
                    # Изменяем тип колонки source на TEXT для поддержки длинных значений
                    cursor.execute('ALTER TABLE calorie_history ALTER COLUMN source TYPE TEXT')
                    conn.commit()
                    logger.info("Calorie history table migrated successfully")
                else:
                    # Проверяем, нужно ли обновить тип колонки source
                    cursor.execute('''
                        SELECT data_type FROM information_schema.columns 
                        WHERE table_name = 'calorie_history' AND column_name = 'source'
                    ''')
                    result = cursor.fetchone()
                    if result and 'character varying' in result[0]:
                        logger.info("Updating source column type to TEXT...")
                        cursor.execute('ALTER TABLE calorie_history ALTER COLUMN source TYPE TEXT')
                        conn.commit()
                        logger.info("Source column type updated successfully")
                    else:
                        logger.info("Calorie history table structure is up to date")
                
                # Принудительно проверяем и исправляем тип колонки source
                logger.info("Force checking source column type...")
                try:
                    # Сначала проверяем текущий тип колонки
                    cursor.execute('''
                        SELECT data_type, character_maximum_length 
                        FROM information_schema.columns 
                        WHERE table_name = 'calorie_history' AND column_name = 'source'
                    ''')
                    result = cursor.fetchone()
                    if result:
                        data_type, max_length = result
                        logger.info(f"Current source column type: {data_type}, max_length: {max_length}")
                        
                        # Если это VARCHAR с ограничением, изменяем на TEXT
                        if 'character varying' in data_type and max_length and max_length < 1000:
                            logger.info("Converting VARCHAR to TEXT...")
                            cursor.execute('ALTER TABLE calorie_history ALTER COLUMN source TYPE TEXT')
                            conn.commit()
                            logger.info("Source column type updated to TEXT")
                        else:
                            logger.info("Source column type is already suitable")
                    else:
                        logger.info("Source column not found, creating as TEXT")
                        cursor.execute('ALTER TABLE calorie_history ALTER COLUMN source TYPE TEXT')
                        conn.commit()
                except Exception as e:
                    logger.error(f"Error updating source column type: {e}")
                    # Попробуем альтернативный способ
                    try:
                        cursor.execute('ALTER TABLE calorie_history ALTER COLUMN source TYPE VARCHAR(1000)')
                        conn.commit()
                        logger.info("Source column type updated to VARCHAR(1000)")
                    except Exception as e2:
                        logger.error(f"Alternative update also failed: {e2}")
                
                # Удаляем столбец workouts_per_week если он существует
                logger.info("Checking for workouts_per_week column...")
                try:
                    cursor.execute('''
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = 'workouts_per_week'
                    ''')
                    result = cursor.fetchone()
                    if result:
                        logger.info("Found workouts_per_week column, removing it...")
                        cursor.execute('ALTER TABLE users DROP COLUMN workouts_per_week')
                        conn.commit()
                        logger.info("workouts_per_week column removed successfully")
                    else:
                        logger.info("workouts_per_week column not found, no action needed")
                except Exception as e:
                    logger.info(f"workouts_per_week column removal: {e}")
            else:
                # Для SQLite проверяем существование колонки
                cursor.execute("PRAGMA table_info(calorie_history)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'food_name' not in columns:
                    logger.info("Migrating SQLite calorie_history table structure...")
                    # Создаем новую таблицу с правильной структурой
                    cursor.execute('''
                        CREATE TABLE calorie_history_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            food_name TEXT,
                            calories INTEGER,
                            source TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    ''')
                    
                    # Копируем данные из старой таблицы
                    cursor.execute('''
                        INSERT INTO calorie_history_new (id, user_id, calories, food_name, source, created_at)
                        SELECT id, user_id, calories, meal_type, description, created_at
                        FROM calorie_history
                    ''')
                    
                    # Удаляем старую таблицу и переименовываем новую
                    cursor.execute('DROP TABLE calorie_history')
                    cursor.execute('ALTER TABLE calorie_history_new RENAME TO calorie_history')
                    conn.commit()
                    logger.info("SQLite calorie history table migrated successfully")
                else:
                    logger.info("SQLite calorie history table structure is up to date")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error migrating calorie_history table: {e}")
    
    def add_user(self, user_data: Dict[str, Any]) -> bool:
        """Добавление или обновление пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, name, gender, 
                                    age, height, weight, activity_level, daily_calories)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        name = EXCLUDED.name,
                        gender = EXCLUDED.gender,
                        age = EXCLUDED.age,
                        height = EXCLUDED.height,
                        weight = EXCLUDED.weight,
                        activity_level = EXCLUDED.activity_level,
                        daily_calories = EXCLUDED.daily_calories,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_data['user_id'], user_data.get('username'), user_data.get('first_name'),
                    user_data.get('last_name'), user_data.get('name'), user_data.get('gender'),
                    user_data.get('age'), user_data.get('height'), user_data.get('weight'),
                    user_data.get('activity_level'), user_data.get('daily_calories')
                ))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, name, gender, 
                                                age, height, weight, activity_level, daily_calories)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['user_id'], user_data.get('username'), user_data.get('first_name'),
                    user_data.get('last_name'), user_data.get('name'), user_data.get('gender'),
                    user_data.get('age'), user_data.get('height'), user_data.get('weight'),
                    user_data.get('activity_level'), user_data.get('daily_calories')
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"User {user_data['user_id']} added/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = %s' if self.use_postgres else 'SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                user_data = dict(zip(columns, row))
                conn.close()
                return user_data
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def add_calorie_record(self, user_id: int, food_name: str, calories: int, source: str = "unknown") -> bool:
        """Добавление записи о калориях"""
        try:
            # Упрощаем данные - только название приема пищи и калории
            # Обрезаем название до 50 символов для краткости
            max_food_name_length = 50
            
            if len(food_name) > max_food_name_length:
                food_name = food_name[:max_food_name_length-3] + "..."
                logger.warning(f"Food name truncated to {max_food_name_length} characters")
            
            # Упрощаем source до коротких значений
            source_map = {
                "photo": "фото",
                "text": "текст", 
                "voice": "голос",
                "unknown": "другое"
            }
            source = source_map.get(source, "другое")
            
            logger.info(f"Adding calorie record: user_id={user_id}, food_name={food_name}, calories={calories}, source={source}")
            conn = self.get_connection()
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
            conn.close()
            logger.info(f"Successfully added calorie record for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding calorie record: {e}")
            return False
    
    def get_daily_calories_sum(self, user_id: int) -> int:
        """Получение суммы калорий за сегодня"""
        try:
            logger.info(f"Getting daily calories sum for user {user_id}")
            conn = self.get_connection()
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
            conn.close()
            daily_sum = result[0] if result else 0
            logger.info(f"Daily calories sum for user {user_id}: {daily_sum}")
            return daily_sum
            
        except Exception as e:
            logger.error(f"Error getting daily calories sum: {e}")
            return 0
    
    def get_user_calorie_history(self, user_id: int, limit: int = 50) -> list:
        """Получить историю калорий пользователя"""
        try:
            conn = self.get_connection()
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
            conn.close()
            
            # Преобразуем в список словарей
            history = []
            for record in records:
                history.append({
                    'id': record[0],
                    'user_id': record[1],
                    'food_name': record[2],
                    'calories': record[3],
                    'source': record[4],
                    'created_at': record[5]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting calorie history: {e}")
            return []

    def get_user_calorie_history_by_period(self, user_id: int, start_date, end_date) -> list:
        """Получение истории калорий пользователя за определенный период"""
        try:
            conn = self.get_connection()
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

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            conn.close()
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Error getting calorie history by period: {e}")
            return []
    
    def get_weekly_calories_summary(self, user_id: int) -> dict:
        """Получение недельной сводки калорий по дням"""
        try:
            conn = self.get_connection()
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
            conn.close()
            
            # Преобразуем в словарь
            weekly_data = {}
            total_weekly = 0
            
            for row in rows:
                date, daily_total, meals_count = row
                weekly_data[str(date)] = {
                    'calories': daily_total or 0,
                    'meals': meals_count or 0
                }
                total_weekly += daily_total or 0
            
            return {
                'daily_data': weekly_data,
                'total_weekly': total_weekly,
                'days_count': len(weekly_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly calories summary: {e}")
            return {'daily_data': {}, 'total_weekly': 0, 'days_count': 0}
    
    def reset_daily_calories(self, user_id: int) -> bool:
        """Сброс калорий за сегодняшний день"""
        try:
            conn = self.get_connection()
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
            conn.close()
            logger.info(f"Daily calories reset for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting daily calories: {e}")
            return False
    
    def clean_corrupted_data(self) -> bool:
        """Очистка поврежденных данных в базе"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                # Для PostgreSQL используем регулярное выражение
                cursor.execute('''
                    DELETE FROM calorie_history 
                    WHERE calories::text !~ '^[0-9]+$'
                ''')
            else:
                # Для SQLite используем GLOB
                cursor.execute('''
                    DELETE FROM calorie_history 
                    WHERE calories NOT GLOB '[0-9]*'
                ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
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
            
            # Коэффициенты активности
            activity_multipliers = {
                'Офисная работа (сидячий образ жизни)': 1.2,
                'Легкая активность (1-3 тренировки в неделю)': 1.375,
                'Умеренная активность (3-5 тренировок в неделю)': 1.55,
                'Высокая активность (6-7 тренировок в неделю)': 1.725,
                'Физическая работа (очень высокая активность)': 1.9
            }
            
            multiplier = activity_multipliers.get(activity_level, 1.2)
            daily_calories = int(bmr * multiplier)
            
            logger.info(f"Calculated daily calories: {daily_calories} for {gender}, age {age}, height {height}, weight {weight}, activity {activity_level}")
            return daily_calories
            
        except Exception as e:
            logger.error(f"Error calculating daily calories: {e}")
            return 2000  # Значение по умолчанию
    
    def reset_user_data(self, user_id: int) -> bool:
        """Полный сброс данных пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Удаляем историю калорий
            if self.use_postgres:
                cursor.execute('DELETE FROM calorie_history WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
            else:
                cursor.execute('DELETE FROM calorie_history WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"User {user_id} data reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting user data: {e}")
            return False
