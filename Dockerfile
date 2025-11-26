FROM python:3.12-slim

WORKDIR /app

# Cài đặt các package hệ thống cần thiết (nếu bot dùng chrome thì thêm sau)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
