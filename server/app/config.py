import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
LOG_BOT_TOKEN = os.getenv("LOG_BOT_TOKEN", "")
CHECKER_BOT_TOKEN = os.getenv("CHECKER_BOT_TOKEN", "")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
LOGS_ID = int(os.getenv("LOGS_ID", "0")) if os.getenv("LOGS_ID") else 0
SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "0")) if os.getenv("SUPPORT_GROUP_ID") else 0
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
DB_PATH = "users.db"

# Pyrogram credentials для парсинга подарков
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# TON Payments
TON_MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "UQA3XG-IIuVK9VetB8iUft4aavAT1OSyBmoT9ipWh9PUCN5Y")
