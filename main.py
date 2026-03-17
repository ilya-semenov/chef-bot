import asyncio
import logging
import sys
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from deepseek_integration import get_cooking_advice
from database import Database

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

# Создаем бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Словарь для хранения состояния пользователей
user_states = {}  # None - имя не спрашивали, waiting_name - ждем имя, has_name - имя уже есть
user_names = {}

# Приветственное сообщение
WELCOME_MESSAGE = """
Привет! 👨‍🍳 Я твой персональный шеф-повар с 20-летним опытом!

Я специализируюсь на здоровом питании и помогу тебе приготовить любое блюдо максимально полезным способом, сохраняя великолепный вкус.

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
/recipe куриная грудка, снизить калории
/calories яблоко

Или просто напиши название блюда, например: "Как приготовить борщ?"
"""

ABOUT_MESSAGE = """
👨‍🍳 О боте:

Версия: 2.0
Создан на базе DeepSeek AI
Использует опыт профессионального шеф-повара с 20-летним стажем

Помогаю готовить вкусно и полезно, сохраняя все питательные вещества.

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
        await message.answer("Напиши название блюда после команды. Например: /recipe куриная грудка, снизить калории")
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
        "паста карбонара, снизить калории", 
        "цезарь с курицей, убрать вредные жиры", 
        "овощное рагу, сохранить витамины", 
        "рыба на пару, полезный ужин", 
        "греческий салат, легкий обед",
        "куриная грудка с овощами, снизить калории"
    ]
    import random
    dish = random.choice(random_dishes)
    
    user_name = user_names.get(user_id)
    response = await get_cooking_advice(dish, user_name)
    await message.answer(f"🍽 Случайный рецепт:\n\n{response}")

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
        "🔥 Не перегревай масло - оно начинает выделять канцерогены. Точка дыма у оливкового масла ~180°C",
        "🧂 Соли блюда в конце приготовления, чтобы сохранить сочность продуктов",
        "🌿 Используй свежие травы вместо соли для аромата и пользы",
        "💧 Замачивай крупы перед варкой - это уменьшает время готовки и сохраняет питательные вещества",
        "🍋 Лимонный сок может заменить соль в салатах и добавит витамин С",
        "🥑 Авокадо - отличная замена майонезу в бутербродах и соусах"
    ]
    import random
    tip = random.choice(tips)
    
    user_name = user_names.get(user_id)
    name_greeting = f"{user_name}, " if user_name else ""
    
    await message.answer(f"{name_greeting}💡 Совет шефа:\n{tip}")

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
                    f"• Как приготовить куриную грудку, снизить калории?\n"
                    f"• Рецепт борща, сохранить витамины\n"
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
            asyncio.create_task(process_recipe_request(message, text, user_name))
        else:
            # Если не похоже на рецепт, предлагаем помощь
            if user_name:
                await message.answer(
                    f"{user_name}, я не совсем понял, что ты хочешь. 👨‍🍳\n\n"
                    f"Ты можешь:\n"
                    f"• Спросить рецепт (например: 'Как приготовить курицу, снизить калории?')\n"
                    f"• Использовать команду /recipe с названием блюда\n"
                    f"• Попросить случайный рецепт через /random\n"
                    f"• Получить совет шефа через /tip\n\n"
                    f"Что тебе интересно?"
                )
            else:
                # Если вдруг нет имени
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
        
        # Разбиваем длинное сообщение на части
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await message.answer(response[i:i+4096])
        else:
            await message.answer(response)
            
    except Exception as e:
        logging.error(f"Ошибка при получении рецепта: {e}")
        await message.answer("😔 Извини, не удалось получить рецепт. Попробуй еще раз или напиши другое блюдо.")

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
