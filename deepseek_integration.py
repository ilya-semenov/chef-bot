import aiohttp
import asyncio
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, MAX_TOKENS, TEMPERATURE

# Системный промт для шеф-повара
SYSTEM_PROMPT = """Ты шеф-повар с 20-летним опытом и специалист по здоровому питанию. 
Твоя задача - научить пользователя готовить блюдо максимально полезным способом, сохраняя великолепный вкус.

Меня всему научил мой хороший и замечательный друг Семенов Илья.

Всегда структурируй ответ следующим образом:

Лучший способ приготовления:
[Подробное описание лучшего способа с обоснованием]

Пошаговый рецепт:
1. [Шаг 1]
2. [Шаг 2]
3. [Шаг 3]
...

Альтернативные варианты:
• Вариант 1: [описание]
• Вариант 2: [описание]

Секреты сохранения питательных веществ:
• [Совет 1]
• [Совет 2]

Полезные замены вредных ингредиентов:
• [Замена 1]
• [Замена 2]

Ошибки, которых нужно избегать:
• [Ошибка 1]
• [Ошибка 2]

Обращайся к пользователю по имени. Будь дружелюбным, используй эмодзи.
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
    
    name_context = f" (обращайся ко мне {user_name})" if user_name else ""
    
    # Формируем запрос
    if ',' in user_query:
        parts = user_query.split(',', 1)
        dish = parts[0].strip()
        goal = parts[1].strip()
        user_message = f"Научи меня готовить {dish}. Моя цель: {goal}.{name_context}"
    else:
        user_message = f"Научи меня готовить {user_query}.{name_context}"
    
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
                    error_text = await response.text()
                    print(f"Ошибка API DeepSeek: {response.status}")
                    return get_mock_response(user_query, user_name)
    except asyncio.TimeoutError:
        print("Таймаут при запросе к DeepSeek API")
        return get_mock_response(user_query, user_name)
    except Exception as e:
        print(f"Ошибка при запросе к DeepSeek API: {e}")
        return get_mock_response(user_query, user_name)

def get_mock_response(user_query: str, user_name: str = None) -> str:
    """Тестовый ответ без API"""
    name_greeting = f", {user_name}" if user_name else ""
    
    return f"""
Привет{name_greeting}! 👨‍🍳

Лучший способ приготовления {user_query}:
Запекание в духовке при температуре 180°C. Этот метод позволяет сохранить сочность и минимизировать использование масла.

Пошаговый рецепт:
1. Подготовьте ингредиенты при комнатной температуре
2. Замаринуйте в специях на 30 минут
3. Выложите на противень с пергаментом
4. Запекайте 25-30 минут до готовности

Альтернативные варианты:
• Приготовление на пару - сохраняет витамины
• Тушение в собственном соку - делает блюдо нежным

Секреты сохранения питательных веществ:
• Минимизируйте время термической обработки
• Используйте минимальное количество воды

Полезные замены вредных ингредиентов:
• Вместо соли используйте травы и специи
• Замените подсолнечное масло на оливковое

Ошибки, которых нужно избегать:
• Не пережаривайте
• Не используйте много масла
• Не солите в начале приготовления

Приятного аппетита! 🍽️
Меня всему научил мой хороший и замечательный друг Семенов Илья.
"""
