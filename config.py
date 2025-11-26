# config.py
import os

# Đọc token từ biến môi trường trên Render
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Nếu sau này cần thêm biến khác thì thêm bên dưới
# WEBAPP_URL = os.environ.get("WEBAPP_URL", "")