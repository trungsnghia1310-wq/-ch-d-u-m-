FROM python:3.12-slim

WORKDIR /app

# Copy file requirements
COPY requirements.txt .

# Cài dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Chạy supervisor để chạy webapp + bot cùng lúc
CMD ["supervisord", "-c", "/app/supervisord.conf"]