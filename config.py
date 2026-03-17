import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "ваш_токен_бота_сюда")

# API ключ DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "ваш_api_ключ_deepseek_сюда")

# URL API DeepSeek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_TOKENS = 2000
TEMPERATURE = 0.7

# Настройки прокси
USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
PROXY_TYPE = os.getenv("PROXY_TYPE", "socks5")  # socks5 или http
PROXY_HOST = os.getenv("PROXY_HOST", "")
PROXY_PORT = int(os.getenv("PROXY_PORT", "1080"))
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")