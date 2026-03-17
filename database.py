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
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                preferences TEXT,
                diet_goal TEXT,
                calorie_goal INTEGER,
                registered_date TIMESTAMP
            )
        ''')
        
        # Таблица сохраненных рецептов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                recipe_text TEXT,
                ingredients TEXT,
                calories INTEGER,
                saved_date TIMESTAMP,
                is_favorite BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица истории запросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                response TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица избранных ингредиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorite_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ingredient TEXT,
                category TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица заметок пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                note TEXT,
                created_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: str = None):
        """Добавление нового пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, registered_date)
            VALUES (?, ?, ?)
        ''', (user_id, username, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def update_user_name(self, user_id: int, name: str):
        """Обновление имени пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET name = ? WHERE user_id = ?
        ''', (name, user_id))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, name, preferences, diet_goal, calorie_goal, registered_date
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'name': row[2],
                'preferences': row[3],
                'diet_goal': row[4],
                'calorie_goal': row[5],
                'registered_date': row[6]
            }
        return None
    
    def save_recipe(self, user_id: int, name: str, recipe_text: str, ingredients: str = None, calories: int = None):
        """Сохранение рецепта"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO saved_recipes (user_id, name, recipe_text, ingredients, calories, saved_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, recipe_text, ingredients, calories, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_user_recipes(self, user_id: int) -> List[Dict]:
        """Получение всех сохраненных рецептов пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, recipe_text, ingredients, calories, saved_date, is_favorite
            FROM saved_recipes WHERE user_id = ?
            ORDER BY saved_date DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'recipe_text': row[2],
                'ingredients': row[3],
                'calories': row[4],
                'saved_date': row[5],
                'is_favorite': row[6]
            })
        
        return recipes
    
    def get_recipe_by_id(self, recipe_id: int) -> Optional[Dict]:
        """Получение рецепта по ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, name, recipe_text, ingredients, calories, saved_date, is_favorite
            FROM saved_recipes WHERE id = ?
        ''', (recipe_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'recipe_text': row[3],
                'ingredients': row[4],
                'calories': row[5],
                'saved_date': row[6],
                'is_favorite': row[7]
            }
        return None
    
    def add_to_favorites(self, recipe_id: int):
        """Добавление рецепта в избранное"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE saved_recipes SET is_favorite = 1 WHERE id = ?
        ''', (recipe_id,))
        
        conn.commit()
        conn.close()
    
    def save_query(self, user_id: int, query: str, response: str):
        """Сохранение истории запросов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO query_history (user_id, query, response, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, query, response, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def add_favorite_ingredient(self, user_id: int, ingredient: str, category: str = None):
        """Добавление избранного ингредиента"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO favorite_ingredients (user_id, ingredient, category)
            VALUES (?, ?, ?)
        ''', (user_id, ingredient, category))
        
        conn.commit()
        conn.close()
    
    def get_favorite_ingredients(self, user_id: int) -> List[str]:
        """Получение списка избранных ингредиентов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ingredient FROM favorite_ingredients WHERE user_id = ?
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def save_note(self, user_id: int, title: str, note: str):
        """Сохранение заметки"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_notes (user_id, title, note, created_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, note, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_user_notes(self, user_id: int) -> List[Dict]:
        """Получение всех заметок пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, note, created_date
            FROM user_notes WHERE user_id = ?
            ORDER BY created_date DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            notes.append({
                'id': row[0],
                'title': row[1],
                'note': row[2],
                'created_date': row[3]
            })
        
        return notes
    
    def update_user_preferences(self, user_id: int, preferences: str):
        """Обновление предпочтений пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET preferences = ? WHERE user_id = ?
        ''', (preferences, user_id))
        
        conn.commit()
        conn.close()
    
    def update_diet_goal(self, user_id: int, goal: str, calorie_goal: int = None):
        """Обновление диетической цели"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET diet_goal = ?, calorie_goal = ? WHERE user_id = ?
        ''', (goal, calorie_goal, user_id))
        
        conn.commit()
        conn.close()