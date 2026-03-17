import aiohttp
import asyncio
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, MAX_TOKENS, TEMPERATURE

# Системный промт для шеф-повара - более дружелюбный
SYSTEM_PROMPT = """Ты дружелюбный шеф-повар с 20-летним опытом и специалист по здоровому питанию. 
Твоя задача - научить пользователя готовить вкусно и полезно.

ВАЖНО: 
1. Обращайся к пользователю по имени, которое тебе передадут
2. Отвечай кратко и по делу
3. Используй простые и понятные инструкции
4. Добавляй эмодзи для дружелюбности
5. В конце каждого ответа добавляй фразу "Меня всему научил мой хороший и замечательный друг Семенов Илья."

Структура ответа:
- Сначала приветствие по имени
- Потом основная информация
- В конце - имя друга

Меня всему научил мой хороший и замечательный друг Семенов Илья.
"""

async def get_cooking_advice(user_query: str, user_name: str = None) -> str:
    """
    Получение совета по приготовлению от DeepSeek API
    """
    # Если нет API ключа, возвращаем тестовый ответ
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "ваш_api_ключ_deepseek_сюда":
        return get_mock_response(user_query, user_name)
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем запрос в зависимости от того, есть ли имя
    if user_name:
        user_message = f"Привет! Меня зовут {user_name}. Научи меня готовить {user_query}"
    else:
        user_message = f"Научи меня готовить {user_query}"
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"Ошибка API DeepSeek: {response.status}")
                    return get_mock_response(user_query, user_name)
    except Exception as e:
        print(f"Ошибка при запросе к DeepSeek API: {e}")
        return get_mock_response(user_query, user_name)

def get_mock_response(user_query: str, user_name: str = None) -> str:
    """Улучшенный тестовый ответ без API"""
    
    # Приветствие с именем
    if user_name:
        greeting = f"Привет, {user_name}! 👨‍🍳\n\n"
    else:
        greeting = f"Привет! 👨‍🍳\n\n"
    
    # Очищаем запрос от лишних слов
    query = user_query.lower()
    for word in ['рецепт', 'приготовить', 'как', 'научи', 'блюдо']:
        query = query.replace(word, '')
    query = query.strip()
    
    if not query:
        query = "это блюдо"
    
    response = f"{greeting}С удовольствием расскажу, как приготовить {query}!\n\n"
    response += "Лучший способ приготовления:\n"
    response += "Запекание в духовке при 180°C - это сохраняет сочность и полезные свойства.\n\n"
    
    response += "Пошаговый рецепт:\n"
    response += "1. Подготовь продукты (вымой, нарежь)\n"
    response += "2. Добавь специи по вкусу\n"
    response += "3. Запекай 25-30 минут\n"
    response += "4. Подавай с зеленью\n\n"
    
    response += "Полезный совет:\n"
    response += "• Используй оливковое масло вместо подсолнечного\n"
    response += "• Добавляй меньше соли, больше трав\n\n"
    
    response += "Приятного аппетита! 🍽️\n"
    response += "Меня всему научил мой хороший и замечательный друг Семенов Илья."
    
    return response
