import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
LOG_BOT_TOKEN = os.getenv("LOG_BOT_TOKEN", "")
LOGS_ID = int(os.getenv("LOGS_ID", "0")) if os.getenv("LOGS_ID") else 0
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
DB_PATH = "users.db"
