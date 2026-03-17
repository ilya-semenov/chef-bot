import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

# Правильный импорт для прокси
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector

from config import BOT_TOKEN, USE_PROXY, PROXY_TYPE, PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD
from deepseek_integration import get_cooking_advice, get_nutrition_info, get_recipe_recommendations
from database import Database
import ssl
import certifi

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
db = Database()

# Состояния для FSM
class RecipeStates(StatesGroup):
    waiting_for_recipe_name = State()
    waiting_for_save_name = State()
    waiting_for_ingredients = State()
    waiting_for_calorie_goal = State()

# Функция для создания бота с прокси или без
async def create_bot():
    """Создает бота с прокси или без"""
    if USE_PROXY:
        try:
            # Формируем URL прокси
            proxy_url = f"{PROXY_TYPE}://"
            if PROXY_USERNAME and PROXY_PASSWORD:
                proxy_url += f"{PROXY_USERNAME}:{PROXY_PASSWORD}@"
            proxy_url += f"{PROXY_HOST}:{PROXY_PORT}"
            
            logging.info(f"Попытка подключения через прокси: {proxy_url}")
            
            # Создаем connector с прокси
            connector = ProxyConnector.from_url(proxy_url)
            
            # Создаем сессию с прокси
            session = ClientSession(connector=connector)
            
            # Создаем бота с сессией
            bot = Bot(
                token=BOT_TOKEN, 
                session=session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            
            logging.info("✅ Бот успешно подключен через прокси")
            return bot
        except Exception as e:
            logging.error(f"❌ Ошибка подключения через прокси: {e}")
            logging.info("Запуск без прокси...")
            return create_bot_without_proxy()
    else:
        return create_bot_without_proxy()

def create_bot_without_proxy():
    """Создает бота без прокси"""
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logging.info("✅ Бот запущен без прокси")
    return bot

# Функция для проверки подключения
async def test_connection(bot: Bot):
    """Тестирует подключение к Telegram API"""
    try:
        me = await bot.get_me()
        logging.info(f"✅ Бот @{me.username} успешно подключен к Telegram API")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к Telegram API: {e}")
        return False

# Приветственное сообщение
WELCOME_MESSAGE = """
Привет! 👨‍🍳 Я твой персональный шеф-повар с 20-летним опытом!

Я специализируюсь на здоровом питании и помогу тебе приготовить любое блюдо максимально полезным способом, сохраняя великолепный вкус.

Меня всему научил мой замечательный шеф и друг Семенов Илья.

Что я умею:
🍳 Давать рецепты с учетом твоих целей
📊 Рассчитывать калорийность и питательную ценность
❤️ Сохранять твои любимые рецепты
🔍 Искать рецепты по ингредиентам
📋 Составлять меню на неделю
⚖️ Помогать с диетическим питанием

Как тебя зовут? Напиши свое имя, чтобы я мог к тебе обращаться.
"""

HELP_MESSAGE = """
🍳 Команды бота:

Основные команды:
/start - Начать работу
/help - Показать это сообщение
/about - О боте

Рецепты:
/recipe [название] - Получить рецепт блюда
/save - Сохранить текущий рецепт в избранное
/myrecipes - Показать сохраненные рецепты
/random - Случайный рецепт

Питание и диеты:
/calories [продукт] - Узнать калорийность
/diet [цель] - Подобрать диету
/mealplan - Составить меню на неделю
/ingredients [ингредиенты] - Найти рецепты по ингредиентам

Советы:
/tip - Получить совет шеф-повара
/substitute [ингредиент] - Чем заменить продукт
"""

ABOUT_MESSAGE = """
👨‍🍳 О боте:

Версия: 2.0
Создан на базе DeepSeek AI
Использует опыт профессионального шеф-повара с 20-летним стажем

Меня всему научил мой замечательный шеф и друг Семенов Илья.

Функции:
• Интеграция с DeepSeek AI
• База данных рецептов SQLite
• Калькулятор калорий
• Планировщик питания

Приятного аппетита! 🍽️
"""

# Клавиатуры
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Случайный рецепт", callback_data="random_recipe")],
        [InlineKeyboardButton(text="📋 Мои рецепты", callback_data="my_recipes")],
        [InlineKeyboardButton(text="📊 Расчет калорий", callback_data="calculate_calories")],
        [InlineKeyboardButton(text="💡 Совет шефа", callback_data="chef_tip")],
        [InlineKeyboardButton(text="📅 Меню на неделю", callback_data="weekly_menu")]
    ])
    return keyboard

async def main():
    """Основная функция запуска бота"""
    # Инициализация БД
    db.init_db()
    
    # Создаем бота
    bot = await create_bot()
    
    # Проверяем подключение
    if not await test_connection(bot):
        logging.error("❌ Не удалось подключиться к Telegram API. Проверьте прокси или интернет.")
        return
    
    # Создаем диспетчер
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем обработчики
    @dp.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Добавляем пользователя в БД если его нет
        db.add_user(user_id, username)
        
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
    async def cmd_recipe(message: Message, state: FSMContext):
        """Получение рецепта по названию"""
        await bot.send_chat_action(message.chat.id, action="typing")
        
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Напиши название блюда после команды. Например: /recipe куриная грудка")
            return
        
        dish_name = parts[1]
        user_data = db.get_user(message.from_user.id)
        user_name = user_data['name'] if user_data and user_data['name'] else None
        
        # Запускаем фоновую обработку
        asyncio.create_task(process_recipe_request(message, state, dish_name, user_name))

    @dp.message(Command("random"))
    async def cmd_random(message: Message):
        """Случайный рецепт"""
        await bot.send_chat_action(message.chat.id, action="typing")
        
        random_dishes = ["паста карбонара", "цезарь с курицей", "овощное рагу", "рыба на пару", "греческий салат"]
        import random
        dish = random.choice(random_dishes)
        
        response = await get_cooking_advice(dish, db.get_user(message.from_user.id)['name'])
        await message.answer(f"🍽 Случайный рецепт: {dish}\n\n{response}")

    @dp.message(Command("calories"))
    async def cmd_calories(message: Message):
        """Узнать калорийность продукта"""
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
        await bot.send_chat_action(message.chat.id, action="typing")
        
        tips = [
            "🥕 Нарезай овощи непосредственно перед приготовлением, чтобы сохранить максимум витаминов",
            "🔥 Не перегревай масло - оно начинает выделять канцерогены",
            "🧂 Соли блюда в конце приготовления, чтобы сохранить сочность",
            "🌿 Используй свежие травы вместо соли для аромата",
            "💧 Замачивай крупы перед варкой - это уменьшает время готовки и сохраняет питательные вещества"
        ]
        import random
        tip = random.choice(tips)
        
        await message.answer(f"💡 Совет шефа:\n{tip}\n\nМеня всему научил мой замечательный шеф и друг Семенов Илья.")

    @dp.message()
    async def handle_message(message: Message, state: FSMContext):
        """Обработчик обычных текстовых сообщений"""
        user_id = message.from_user.id
        user_data = db.get_user(user_id)
        
        # Сразу показываем, что бот печатает
        await bot.send_chat_action(message.chat.id, action="typing")
        
        # Проверяем, не ввел ли пользователь имя
        if not user_data or not user_data['name']:
            if len(message.text) < 30:
                # Сохраняем имя пользователя
                db.update_user_name(user_id, message.text.strip())
                await message.answer(
                    f"Приятно познакомиться, {message.text.strip()}! "
                    f"Теперь ты можешь спрашивать меня о любых блюдах.\n\n"
                    f"Вот что я умею:",
                    reply_markup=get_main_keyboard()
                )
                return
        
        # Если это запрос на рецепт
        if any(word in message.text.lower() for word in ['приготовить', 'рецепт', 'как готовить']):
            asyncio.create_task(process_recipe_request(
                message, state, message.text, 
                user_data['name'] if user_data else None
            ))
        else:
            # Если не знаем, что ответить, показываем меню
            await message.answer(
                f"Я не совсем понял запрос. Вот что я могу сделать:",
                reply_markup=get_main_keyboard()
            )

    async def process_recipe_request(message: Message, state: FSMContext, query: str, user_name: str = None):
        """Фоновая обработка запроса рецепта"""
        try:
            response = await get_cooking_advice(query, user_name)
            await state.update_data(last_recipe=query, last_response=response)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❤️ Сохранить рецепт", callback_data="save_recipe")]
            ])
            
            await message.answer(response, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при получении рецепта: {e}")
            await message.answer("😔 Извини, произошла ошибка при получении рецепта. Попробуй позже.")

    @dp.callback_query()
    async def handle_callback(callback: CallbackQuery, state: FSMContext):
        """Обработка нажатий на кнопки"""
        await bot.answer_callback_query(callback.id)
        
        if callback.data == "random_recipe":
            await cmd_random(callback.message)
        elif callback.data == "calculate_calories":
            await callback.message.answer("Напиши /calories [название продукта] чтобы узнать калорийность")
        elif callback.data == "chef_tip":
            await cmd_tip(callback.message)
        elif callback.data == "save_recipe":
            data = await state.get_data()
            if data.get('last_recipe'):
                await state.set_state(RecipeStates.waiting_for_save_name)
                await callback.message.answer("Введи название для сохранения рецепта:")

    # Запускаем бота
    try:
        logging.info("🚀 Бот запускается...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())