# config.py
import os

"""
File này chỉ lấy biến môi trường từ Render / máy local.
Bạn KHÔNG ghi token thẳng vào code nữa.
"""

# Token bot Telegram (đặt trong Environment: TELEGRAM_BOT_TOKEN)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# URL webapp (đặt trong Environment: WEBAPP_URL)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")  # tạm default cho local