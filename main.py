import asyncio
import logging
import sys
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN, DEEPSEEK_API_KEY
from deepseek_integration import get_cooking_advice
from database import Database
import os

# Глобальный обработчик исключений
def global_exception_handler(exc_type, exc_value, exc_traceback):
    logging.error("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = global_exception_handler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Инициализация базы данных
db = Database()

# Создаем бота БЕЗ ПРОКСИ
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Словарь для хранения состояния пользователей
# None - имя не спрашивали, waiting_name - ждем имя, has_name - имя уже есть
user_states = {}
user_names = {}

# Приветственное сообщение
WELCOME_MESSAGE = """
Привет! 👨‍🍳 Я твой персональный шеф-повар с 20-летним опытом!

Я специализируюсь на здоровом питании и помогу тебе приготовить любое блюдо максимально полезным способом, сохраняя великолепный вкус.

Меня всему научил мой хороший и замечательный друг Семенов Илья.

Как тебя зовут? Напиши свое имя, чтобы я мог к тебе обращаться.
"""

HELP_MESSAGE = """
🍳 Команды бота:

/start - Начать работу (спросит имя)
/help - Показать это сообщение
/about - О боте
/recipe [название] - Получить рецепт блюда
/random - Случайный рецепт
/calories [продукт] - Узнать калорийность
/tip - Получить совет шефа

Примеры:
/recipe куриная грудка
/calories яблоко

Или просто напиши название блюда, например: "Как приготовить борщ?"
"""

ABOUT_MESSAGE = """
👨‍🍳 О боте:

Версия: 2.0
Создан на базе DeepSeek AI
Использует опыт профессионального шеф-повара с 20-летним стажем

Меня всему научил мой хороший и замечательный друг Семенов Илья.

Приятного аппетита! 🍽️
"""

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Устанавливаем состояние "ждем имя"
    user_states[user_id] = "waiting_name"
    
    logging.info(f"Пользователь {user_id} запустил бота, ждем имя")
    await message.answer(WELCOME_MESSAGE)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(HELP_MESSAGE)

@dp.message(Command("about"))
async def cmd_about(message: Message):
    """Обработчик команды /about"""
    await message.answer(ABOUT_MESSAGE)

@dp.message(Command("recipe"))
async def cmd_recipe(message: Message):
    """Получение рецепта по названию"""
    user_id = message.from_user.id
    
    # Проверяем, знаем ли мы имя пользователя
    if user_id not in user_names:
        user_states[user_id] = "waiting_name"
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши название блюда после команды. Например: /recipe куриная грудка")
        return
    
    dish_name = parts[1]
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, action="typing")
    
    # Получаем имя пользователя
    user_name = user_names.get(user_id)
    
    # Запускаем фоновую задачу для получения рецепта
    asyncio.create_task(process_recipe_request(message, dish_name, user_name))

@dp.message(Command("random"))
async def cmd_random(message: Message):
    """Случайный рецепт"""
    user_id = message.from_user.id
    
    # Проверяем, знаем ли мы имя пользователя
    if user_id not in user_names:
        user_states[user_id] = "waiting_name"
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    random_dishes = [
        "паста карбонара", 
        "цезарь с курицей", 
        "овощное рагу", 
        "рыба на пару", 
        "греческий салат",
        "куриная грудка с овощами",
        "омлет с помидорами",
        "тыквенный суп"
    ]
    import random
    dish = random.choice(random_dishes)
    
    user_name = user_names.get(user_id)
    response = await get_cooking_advice(dish, user_name)
    await message.answer(f"🍽 Случайный рецепт: {dish}\n\n{response}")

@dp.message(Command("calories"))
async def cmd_calories(message: Message):
    """Узнать калорийность продукта"""
    user_id = message.from_user.id
    
    # Проверяем, знаем ли мы имя пользователя
    if user_id not in user_names:
        user_states[user_id] = "waiting_name"
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши продукт после команды. Например: /calories яблоко")
        return
    
    food = parts[1]
    await bot.send_chat_action(message.chat.id, action="typing")
    
    nutrition_info = await get_nutrition_info(food)
    await message.answer(nutrition_info)

@dp.message(Command("tip"))
async def cmd_tip(message: Message):
    """Получить совет шефа"""
    user_id = message.from_user.id
    
    # Проверяем, знаем ли мы имя пользователя
    if user_id not in user_names:
        user_states[user_id] = "waiting_name"
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    tips = [
        "🥕 Нарезай овощи непосредственно перед приготовлением, чтобы сохранить максимум витаминов",
        "🔥 Не перегревай масло - оно начинает выделять канцерогены",
        "🧂 Соли блюда в конце приготовления, чтобы сохранить сочность",
        "🌿 Используй свежие травы вместо соли для аромата",
        "💧 Замачивай крупы перед варкой - это уменьшает время готовки и сохраняет питательные вещества",
        "🍋 Лимонный сок может заменить соль в салатах",
        "🥑 Авокадо - отличная замена майонезу в бутербродах"
    ]
    import random
    tip = random.choice(tips)
    
    user_name = user_names.get(user_id)
    name_greeting = f", {user_name}" if user_name else ""
    
    await message.answer(f"💡 Совет шефа для тебя{name_greeting}:\n{tip}\n\nМеня всему научил мой хороший и замечательный друг Семенов Илья.")

@dp.message()
async def handle_message(message: Message):
    """Обработчик обычных текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        # Проверяем состояние пользователя
        if user_id in user_states and user_states[user_id] == "waiting_name":
            # Пользователь должен ввести имя
            if len(text) < 30 and not any(word in text.lower() for word in ['рецепт', 'блюдо', 'как', 'приготовить', '/']):
                # Сохраняем имя
                user_names[user_id] = text
                user_states[user_id] = "has_name"
                
                # Сохраняем в БД
                try:
                    db.add_user(user_id, message.from_user.username)
                    db.update_user_name(user_id, text)
                except Exception as e:
                    logging.error(f"Ошибка сохранения имени в БД: {e}")
                
                await message.answer(
                    f"Приятно познакомиться, {text}! 👋\n\n"
                    f"Теперь ты можешь спрашивать меня о любых блюдах. Например:\n"
                    f"• Как приготовить куриную грудку?\n"
                    f"• Рецепт борща\n"
                    f"• Омлет с овощами\n\n"
                    f"Что хочешь приготовить сегодня?"
                )
                return
            else:
                # То, что написал пользователь, не похоже на имя
                await message.answer(
                    "Я не совсем понял. Напиши, пожалуйста, свое имя (просто имя, без лишних слов):\n\n"
                    "Например: Анна, Иван, Мария..."
                )
                return
        
        # Если имя уже есть, обрабатываем запрос
        user_name = user_names.get(user_id)
        
        # Показываем, что бот печатает
        await bot.send_chat_action(message.chat.id, action="typing")
        
        # Проверяем, похоже ли сообщение на запрос о рецепте
        recipe_keywords = ['рецепт', 'приготовить', 'как', 'блюдо', 'сварить', 'пожарить', 'испечь']
        is_recipe_request = any(word in text.lower() for word in recipe_keywords) or len(text.split()) < 10
        
        if is_recipe_request:
            # Это запрос на рецепт
            await bot.send_chat_action(message.chat.id, action="typing")
            asyncio.create_task(process_recipe_request(message, text, user_name))
        else:
            # Если не похоже на рецепт, предлагаем помощь
            if user_name:
                await message.answer(
                    f"{user_name}, я не совсем понял, что ты хочешь. 👨‍🍳\n\n"
                    f"Ты можешь:\n"
                    f"• Спросить рецепт (например: 'Как приготовить курицу?')\n"
                    f"• Использовать команду /recipe с названием блюда\n"
                    f"• Попросить случайный рецепт через /random\n"
                    f"• Узнать калорийность через /calories\n\n"
                    f"Что тебе интересно?"
                )
            else:
                # Если вдруг нет имени (на всякий случай)
                user_states[user_id] = "waiting_name"
                await message.answer(
                    "Привет! 👨‍🍳 Как тебя зовут? Напиши свое имя, чтобы мы могли познакомиться."
                )
            
    except Exception as e:
        logging.error(f"Ошибка в обработчике сообщений: {e}")
        traceback.print_exc()
        await message.answer(
            "😔 Извини, произошла ошибка. Попробуй еще раз или используй /help для просмотра команд."
        )

async def process_recipe_request(message: Message, query: str, user_name: str = None):
    """Фоновая обработка запроса рецепта"""
    try:
        # Показываем, что бот печатает
        await bot.send_chat_action(message.chat.id, action="typing")
        
        # Получаем ответ
        response = await get_cooking_advice(query, user_name)
        
        # Добавляем приветствие с именем если его нет в ответе
        if user_name and f"{user_name}" not in response and "Привет" not in response[:20]:
            response = f"{user_name}, вот рецепт, который ты просил:\n\n{response}"
        
        # Разбиваем длинное сообщение на части
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await message.answer(response[i:i+4096])
        else:
            await message.answer(response)
            
    except Exception as e:
        logging.error(f"Ошибка при получении рецепта: {e}")
        await message.answer("😔 Извини, не удалось получить рецепт. Попробуй еще раз или напиши другое блюдо.")

async def get_nutrition_info(food: str) -> str:
    """Получение информации о питательной ценности продукта"""
    nutrition_db = {
        "яблоко": "🍎 Яблоко (100г): 52 ккал, белки 0.3г, жиры 0.2г, углеводы 14г",
        "банан": "🍌 Банан (100г): 96 ккал, белки 1.5г, жиры 0.2г, углеводы 22г",
        "курица": "🍗 Куриная грудка (100г): 165 ккал, белки 31г, жиры 3.6г, углеводы 0г",
        "рис": "🍚 Рис вареный (100г): 130 ккал, белки 2.7г, жиры 0.3г, углеводы 28г",
        "гречка": "🌾 Гречка вареная (100г): 110 ккал, белки 4.2г, жиры 1.1г, углеводы 21г",
        "картофель": "🥔 Картофель вареный (100г): 86 ккал, белки 1.7г, жиры 0.1г, углеводы 20г",
        "брокколи": "🥦 Брокколи (100г): 34 ккал, белки 2.8г, жиры 0.4г, углеводы 7г",
        "яйцо": "🥚 Яйцо куриное (1 шт): 70 ккал, белки 6г, жиры 5г, углеводы 0.6г",
        "творог": "🥛 Творог 5% (100г): 145 ккал, белки 21г, жиры 5г, углеводы 3г",
        "говядина": "🥩 Говядина (100г): 187 ккал, белки 19г, жиры 12г, углеводы 0г"
    }
    
    food_lower = food.lower()
    for key in nutrition_db:
        if key in food_lower:
            return nutrition_db[key]
    
    return f"🍽 Информация о {food}:\nЯ не нашел точных данных, но в среднем продукты этой категории содержат 50-200 ккал на 100г."

async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация БД
        db.init_db()
        logging.info("✅ База данных инициализирована")
        
        # Проверяем токен
        if not BOT_TOKEN or BOT_TOKEN == "ваш_токен_бота_сюда":
            logging.error("❌ Токен бота не указан в config.py или .env")
            return
        
        logging.info(f"🚀 Бот запускается...")
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logging.error(f"❌ Критическая ошибка при запуске: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        traceback.print_exc()
