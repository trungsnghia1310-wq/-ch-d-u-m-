FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Start supervisor (run bot + web)
CMD ["supervisord", "-c", "/app/supervisord.conf"]