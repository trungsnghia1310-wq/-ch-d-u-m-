import os  # NHỚ DÒNG NÀY

# Lấy biến môi trường từ Render (hoặc máy local)
BOT_TOKEN  = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Nếu bạn có thêm biến khác thì thêm tiếp:
# AYET_API   = os.getenv("AYET_API")
# GITLAB_KEY = os.getenv("GITLAB_KEY")