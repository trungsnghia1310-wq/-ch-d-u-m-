FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy toàn bộ source code (bao gồm oil_mining_bot/, static/, webapp_main.py, supervisord.conf)
COPY . .

CMD ["supervisord", "-n", "-c", "/app/supervisord.conf"]