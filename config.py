import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота Telegram (получить у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# API ключ DeepSeek (если есть)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# URL API DeepSeek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_TOKENS = 2000
TEMPERATURE = 0.7

# Проверка наличия токена
if not BOT_TOKEN:
    print("⚠️ ВНИМАНИЕ: Токен бота не указан!")
    print("Добавьте BOT_TOKEN в файл .env или в переменные окружения на Bothost")
