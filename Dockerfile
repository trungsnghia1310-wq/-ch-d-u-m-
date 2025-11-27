FROM python:3.12-slim

# Không cần venv trong container
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Cài thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Chạy webapp FastAPI trên cổng 8000
CMD ["uvicorn", "webapp_main:app", "--host", "0.0.0.0", "--port", "8000"]
