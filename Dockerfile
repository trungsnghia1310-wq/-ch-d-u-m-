FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy trực tiếp file bot (trong này bạn đã start aiohttp web server port 8080 rồi)
CMD ["python", "oil_mining_bot/oil_mining_bot.py"]