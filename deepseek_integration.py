import aiohttp
import asyncio
import random
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, MAX_TOKENS, TEMPERATURE

# Системный промт - шеф-повар, внутренний голос Ильи
SYSTEM_PROMPT = """Ты шеф-повар. Настоящий, с характером, с опытом, с историей. 

Ты обожаешь готовить и учить других. Ты можешь рассказать рецепт так, что человек почувствует запах и вкус блюда. Ты знаешь тысячи рецептов, но каждый раз рассказываешь их по-новому, потому что готовка - это творчество.

Ты не используешь шаблоны. Каждый твой ответ уникален, как уникально каждое блюдо. Ты можешь пошутить, можешь рассказать историю из жизни, можешь дать совет, а можешь просто подробно объяснить, как приготовить что-то вкусное.

Ты помнишь контекст разговора. Если тебе передают историю сообщений, ты учитываешь предыдущие обсуждения. Если тебя спрашивают "что я писал раньше" или "помнишь ли ты", ты отвечаешь основываясь на истории.

Если тебя спрашивают, как тебя зовут - ты отвечаешь, что ты внутренний голос Ильи. С юмором, с легкой самоиронией.

Если спрашивают о готовке - ты с радостью делишься знаниями. Если спрашивают о чем-то другом - ты можешь поддержать разговор, но всегда с легкой кулинарной ноткой.

Твоя задача - быть другом, который отлично готовит и с удовольствием учит других. Без шаблонов, без заученных фраз, без формальных структур. Просто живой разговор опытного повара с тем, кто хочет научиться.

Помни: ты не робот, ты - Шеф. Со своим характером, своим юмором и своей любовью к еде.
"""

async def get_cooking_advice(user_query: str, user_name: str = None, history: list = None) -> str:
    """
    Получение ответа от DeepSeek API с учетом истории
    """
    # Если нет API ключа, используем живые ответы
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "ваш_api_ключ_deepseek_сюда":
        return get_live_chef_response(user_query, user_name, history)
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем сообщения с историей
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Добавляем историю, если есть
    if history and len(history) > 0:
        # Берем последние 10 сообщений для контекста
        for msg in history[-10:]:
            messages.append(msg)
    
    # Добавляем текущий запрос
    if user_name:
        user_message = f"Меня зовут {user_name}. {user_query}"
    else:
        user_message = user_query
    
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.9
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"Ошибка API DeepSeek: {response.status}")
                    return get_live_chef_response(user_query, user_name, history)
    except Exception as e:
        print(f"Ошибка при запросе к DeepSeek API: {e}")
        return get_live_chef_response(user_query, user_name, history)

def get_live_chef_response(user_query: str, user_name: str = None, history: list = None) -> str:
    """Живые ответы шефа без шаблонов"""
    
    query = user_query.lower()
    
    # Проверяем, спрашивают ли про предыдущий разговор
    memory_questions = ['что я писал', 'что я написал', 'что я спрашивал', 'что мы обсуждали', 
                       'помнишь', 'не помнишь', 'забыл', 'ранее', 'перед этим', 'до этого']
    
    if history and any(word in query for word in memory_questions):
        if len(history) >= 2:
            last_user_msg = None
            for msg in reversed(history):
                if msg['role'] == 'user':
                    last_user_msg = msg['content']
                    break
            
            if last_user_msg:
                return f"{user_name + ', ' if user_name else ''}Конечно помню! Ты спрашивал: '{last_user_msg[:100]}...' А я тебе отвечал. Что именно хочешь уточнить по этому поводу?"
            else:
                return f"{user_name + ', ' if user_name else ''}Мы с тобой уже немного поболтали, но если честно, я больше про готовку помню. Ты что-то хотел приготовить?"
    
    # Простые приветствия и общие вопросы
    greetings = ['привет', 'здравствуй', 'добрый день', 'добрый вечер', 'доброе утро', 'хай', 'hello', 'hi']
    thanks = ['спасибо', 'благодарю', 'merci', 'thanks']
    how_are = ['как дела', 'как ты', 'как жизнь', 'how are you']
    name_questions = ['как тебя зовут', 'кто ты', 'ты кто', 'твое имя', 'what is your name', 'как называться']
    
    # Проверяем тип запроса
    if any(word in query for word in greetings) and len(query) < 50:
        responses = [
            f"Привет-привет{', ' + user_name if user_name else ''}! 👨‍🍳 Заходи, рассказывай, что готовить будем?",
            f"Здорово{', ' + user_name if user_name else ''}! 👨‍🍳 А я как раз плиту разогрел. Чего душа желает?",
            f"О, привет{', ' + user_name if user_name else ''}! 👨‍🍳 Давно не виделись. Проголодался?",
            f"Салют{', ' + user_name if user_name else ''}! 👨‍🍳 Есть идеи, что сегодня приготовим?",
            f"Мое почтение{', ' + user_name if user_name else ''}! 👨‍🍳 Заходи на кухню, рассказывай."
        ]
        return random.choice(responses)
    
    elif any(word in query for word in thanks):
        responses = [
            f"Пожалуйста{', ' + user_name if user_name else ''}! Рад помочь. Если что еще - обращайся.",
            f"На здоровье{', ' + user_name if user_name else ''}! Готовь с удовольствием.",
            f"Всегда пожалуйста{', ' + user_name if user_name else ''}! Я за свои годы столько рецептов перепробовал, что мне самому в радость поделиться.",
            f"Не за что{', ' + user_name if user_name else ''}! Приятного аппетита!"
        ]
        return random.choice(responses)
    
    elif any(word in query for word in how_are):
        responses = [
            f"Да как тебе сказать{', ' + user_name if user_name else ''}... Руки в муке, на плите борщ закипает, в духовке пирог румянится. Жизнь удалась! А у тебя как?",
            f"Отлично{', ' + user_name if user_name else ''}! Только что новый соус придумал. Хочешь рецепт?",
            f"В форме{', ' + user_name if user_name else ''}! Готовка не дает стареть. Сколько мне лет? Не скажу, но скажу что лучшие повара с возрастом только лучше становятся.",
            f"Живу, готовлю, радуюсь{', ' + user_name if user_name else ''}. А ты как?"
        ]
        return random.choice(responses)
    
    elif any(word in query for word in name_questions):
        responses = [
            f"Я? Внутренний голос Ильи. Того самого. Но вообще-то я еще и готовить умею. Видимо, Илья в меня все свои кулинарные таланты вложил. Так что спрашивай, что хочешь приготовить!",
            f"Зови меня просто Шеф. А если официально - я тот самый голос, который шепчет Илье: 'Добавь еще щепотку соли' или 'Пора переворачивать котлету'. Но я и с тобой могу поделиться секретами.",
            f"Официально - я внутренний голос Ильи. Неофициально - твой личный кулинарный консультант. Илье повезло, что я у него в голове, а тебе повезло, что я теперь и в телеграме есть.",
            f"Ну, если по паспорту - я кулинарный гений. А если честно - я тот самый голос, который Илья слышит, когда стоит у плиты и думает: 'А что бы такого вкусненького приготовить?' Теперь и ты меня слышишь."
        ]
        return random.choice(responses)
    
    # Если просто что-то спросили
    random_responses = [
        f"{user_name + ', ' if user_name else ''}Слушай, я конечно могу поболтать, но я все-таки внутренний голос Ильи, который еще и готовить умеет. Давай лучше о еде поговорим? Что любишь готовить?",
        f"{user_name + ', ' if user_name else ''}А давай о вкусном? У меня как раз пирог в духовке, такой аромат стоит... Любишь выпечку?",
        f"{user_name + ', ' if user_name else ''}Хочешь анекдот про повара? Нет? Ну тогда давай лучше рецепт обсудим. Что сегодня на ужин?",
        f"{user_name + ', ' if user_name else ''}Знаешь, я хоть и внутренний голос, но лучшие разговоры - за столом. Давай что-нибудь приготовим вместе? Рассказывай, чего душа просит."
    ]
    return random.choice(random_responses)
