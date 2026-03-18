import asyncio
import logging
import sys
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
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

# Создаем бота и хранилище состояний
storage = MemoryStorage()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# Определяем состояния для FSM
class ChefStates(StatesGroup):
    waiting_for_name = State()  # Ждем имя
    chatting = State()           # Общаемся

# Словарь для хранения имен пользователей (дублируем для быстрого доступа)
user_names = {}

# Приветственное сообщение
WELCOME_MESSAGE = """
Привет! 👨‍🍳 Я твой персональный шеф-повар с 20-летним опытом!

Я специализируюсь на здоровом питании и помогу тебе приготовить любое блюдо максимально полезным способом, сохраняя великолепный вкус.

Меня создал и всему научил мой наставник, шеф и лучший друг Семенов Илья.

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
/forget - Забыть историю разговора и начать заново

Примеры:
/recipe куриная грудка
/calories яблоко

Или просто напиши название блюда, например: "Как приготовить борщ?"
"""

ABOUT_MESSAGE = """
👨‍🍳 О боте:

Версия: 3.0
Создан на базе DeepSeek AI
Использует опыт профессионального шеф-повара с 20-летним стажем

Меня создал и всему научил мой наставник, шеф и лучший друг Семенов Илья.

Помогаю готовить вкусно и полезно, сохраняя все питательные вещества.
Умею запоминать историю разговора и поддерживать контекст!

Приятного аппетита! 🍽️
"""

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Очищаем историю разговора
    await state.clear()
    
    # Устанавливаем состояние "ждем имя"
    await state.set_state(ChefStates.waiting_for_name)
    
    # Сохраняем информацию о пользователе в БД
    try:
        db.add_user(user_id, message.from_user.username)
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")
    
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

@dp.message(Command("forget"))
async def cmd_forget(message: Message, state: FSMContext):
    """Забыть историю разговора"""
    user_id = message.from_user.id
    user_name = user_names.get(user_id)
    
    # Очищаем историю
    await state.clear()
    
    # Возвращаемся в состояние чата (если имя уже было)
    if user_name:
        await state.set_state(ChefStates.chatting)
        await state.update_data(user_name=user_name)
        await message.answer(f"{user_name}, я все забыл! Давай начнем с чистого листа. О чем поговорим?")
    else:
        await state.set_state(ChefStates.waiting_for_name)
        await message.answer("Ой, а я забыл как тебя зовут! Напомни, пожалуйста.")

@dp.message(Command("recipe"))
async def cmd_recipe(message: Message, state: FSMContext):
    """Получение рецепта по названию"""
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_name = data.get('user_name')
    
    # Если имени нет, просим представиться
    if not user_name and user_id not in user_names:
        await state.set_state(ChefStates.waiting_for_name)
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    # Если имя есть в кеше, но нет в состоянии, восстанавливаем
    if not user_name and user_id in user_names:
        user_name = user_names[user_id]
        await state.update_data(user_name=user_name)
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши название блюда после команды. Например: /recipe куриная грудка")
        return
    
    dish_name = parts[1]
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, action="typing")
    
    # Получаем историю разговора
    history = data.get('history', [])
    
    # Добавляем запрос в историю
    history.append({"role": "user", "content": f"Спросил рецепт: {dish_name}"})
    
    # Запускаем фоновую задачу для получения рецепта
    asyncio.create_task(process_recipe_request(message, state, dish_name, user_name, history))

@dp.message(Command("random"))
async def cmd_random(message: Message, state: FSMContext):
    """Случайный рецепт"""
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_name = data.get('user_name')
    
    # Если имени нет, просим представиться
    if not user_name and user_id not in user_names:
        await state.set_state(ChefStates.waiting_for_name)
        await message.answer("Сначала напиши свое имя, чтобы я мог к тебе обращаться! Как тебя зовут?")
        return
    
    # Если имя есть в кеше, но нет в состоянии, восстанавливаем
    if not user_name and user_id in user_names:
        user_name = user_names[user_id]
        await state.update_data(user_name=user_name)
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    random_dishes = [
        "куриная грудка", 
        "овощное рагу", 
        "рыба на пару", 
        "греческий салат",
        "борщ",
        "паста карбонара"
    ]
    import random
    dish = random.choice(random_dishes)
    
    # Получаем историю
    history = data.get('history', [])
    history.append({"role": "user", "content": f"Попросил случайный рецепт, выбрал {dish}"})
    
    response = await get_cooking_advice(f"Расскажи как приготовить {dish}", user_name, history)
    
    # Сохраняем ответ в историю
    history.append({"role": "assistant", "content": response[:100] + "..."})
    await state.update_data(history=history)
    
    await message.answer(f"🍽 Случайный рецепт:\n\n{response}")

@dp.message(Command("tip"))
async def cmd_tip(message: Message, state: FSMContext):
    """Получить совет шефа"""
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_name = data.get('user_name')
    
    # Если имени нет, просим представиться
    if not user_name and user_id not in user_names:
        await state.set_state(ChefStates.waiting_for_name)
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
    
    name_greeting = f"{user_name}, " if user_name else ""
    
    # Сохраняем в историю
    history = data.get('history', [])
    history.append({"role": "assistant", "content": f"Дал совет: {tip[:50]}..."})
    await state.update_data(history=history)
    
    await message.answer(f"{name_greeting}💡 Совет шефа:\n{tip}")

@dp.message()
async def handle_message(message: Message, state: FSMContext):
    """Обработчик обычных текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    data = await state.get_data()
    user_name = data.get('user_name')
    
    try:
        # Если ждем имя
        if current_state == ChefStates.waiting_for_name.state:
            # Проверяем, что это похоже на имя
            if len(text) < 30 and not any(word in text.lower() for word in ['рецепт', 'блюдо', 'как', 'приготовить', '/', 'готовить']):
                # Сохраняем имя
                user_name = text
                user_names[user_id] = user_name
                
                # Сохраняем в состояние
                await state.update_data(user_name=user_name, history=[])
                await state.set_state(ChefStates.chatting)
                
                # Сохраняем в БД
                try:
                    db.add_user(user_id, message.from_user.username)
                    db.update_user_name(user_id, text)
                except Exception as e:
                    logging.error(f"Ошибка сохранения имени в БД: {e}")
                
                await message.answer(
                    f"Приятно познакомиться, {text}! 👋\n\n"
                    f"Теперь ты можешь спрашивать меня о любых блюдах. Я буду помнить наш разговор!\n\n"
                    f"Например:\n"
                    f"• Как приготовить куриную грудку?\n"
                    f"• Рецепт борща\n"
                    f"• Омлет с овощами\n\n"
                    f"Что хочешь приготовить сегодня?"
                )
                return
            else:
                # Не похоже на имя
                await message.answer(
                    "Я не совсем понял. Напиши, пожалуйста, свое имя (просто имя, без лишних слов):\n\n"
                    "Например: Анна, Иван, Мария..."
                )
                return
        
        # Если уже в режиме чата
        if current_state == ChefStates.chatting.state:
            # Показываем, что бот печатает
            await bot.send_chat_action(message.chat.id, action="typing")
            
            # Получаем историю разговора
            history = data.get('history', [])
            
            # Проверяем, спрашивают ли про предыдущий разговор
            memory_questions = ['что я писал', 'что я написал', 'что я спрашивал', 'что мы обсуждали', 
                               'помнишь', 'не помнишь', 'забыл', 'ранее', 'перед этим', 'до этого',
                               'что ты помнишь', 'о чем мы говорили']
            
            is_memory_question = any(word in text.lower() for word in memory_questions)
            
            if is_memory_question and history:
                # Если спрашивают про историю, отвечаем основываясь на ней
                last_topics = []
                for item in history[-3:]:  # последние 3 события
                    if item['role'] == 'user':
                        last_topics.append(f"Ты спрашивал: {item['content'][:50]}...")
                    else:
                        last_topics.append(f"Я отвечал про {item['content'][:30]}...")
                
                memory_response = f"{user_name + ', ' if user_name else ''}Конечно помню! Мы с тобой говорили о:\n"
                memory_response += "\n".join([f"• {topic}" for topic in last_topics])
                memory_response += "\n\nА что именно тебя интересует?"
                
                await message.answer(memory_response)
                return
            
            # Проверяем, похоже ли на запрос о рецепте
            recipe_keywords = ['рецепт', 'приготовить', 'как', 'блюдо', 'сварить', 'пожарить', 'испечь', 'сделать']
            is_recipe_request = any(word in text.lower() for word in recipe_keywords)
            
            if is_recipe_request:
                # Добавляем запрос в историю
                history.append({"role": "user", "content": text})
                
                # Запускаем обработку с историей
                asyncio.create_task(process_recipe_request(message, state, text, user_name, history))
            else:
                # Просто болтаем
                history.append({"role": "user", "content": text})
                
                # Отправляем в DeepSeek с историей
                response = await get_cooking_advice(
                    text + " (просто болтаем, но можешь вставить кулинарную тему)", 
                    user_name, 
                    history
                )
                
                # Сохраняем ответ в историю
                history.append({"role": "assistant", "content": response[:100] + "..."})
                await state.update_data(history=history)
                
                await message.answer(response)
        else:
            # Если состояние не определено, начинаем заново
            await state.set_state(ChefStates.waiting_for_name)
            await message.answer(WELCOME_MESSAGE)
            
    except Exception as e:
        logging.error(f"Ошибка в обработчике сообщений: {e}")
        traceback.print_exc()
        await message.answer(
            "😔 Извини, произошла ошибка. Попробуй еще раз или используй /help для просмотра команд."
        )

async def process_recipe_request(message: Message, state: FSMContext, query: str, user_name: str = None, history: list = None):
    """Фоновая обработка запроса рецепта"""
    try:
        # Показываем, что бот печатает
        await bot.send_chat_action(message.chat.id, action="typing")
        
        if history is None:
            data = await state.get_data()
            history = data.get('history', [])
        
        # Получаем ответ с учетом истории
        response = await get_cooking_advice(query, user_name, history)
        
        # Сохраняем ответ в историю
        history.append({"role": "assistant", "content": response[:100] + "..."})
        await state.update_data(history=history)
        
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
