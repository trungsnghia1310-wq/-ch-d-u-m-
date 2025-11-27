import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://chdum.fly.dev")
CREDIT_SECRET = os.getenv("CREDIT_SECRET", "")
DB_PATH = os.getenv("DB_PATH", "app.sqlite3")