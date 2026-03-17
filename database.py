import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_name="chef_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    registered_date TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print(f"✅ База данных {self.db_name} инициализирована")
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
    
    def add_user(self, user_id: int, username: str = None):
        """Добавление нового пользователя"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, registered_date)
                VALUES (?, ?, ?)
            ''', (user_id, username, datetime.now()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка добавления пользователя: {e}")
    
    def update_user_name(self, user_id: int, name: str):
        """Обновление имени пользователя"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET name = ? WHERE user_id = ?
            ''', (name, user_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка обновления имени: {e}")
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, name, registered_date
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'registered_date': row[3]
                }
            return None
        except Exception as e:
            print(f"Ошибка получения пользователя: {e}")
            return None
