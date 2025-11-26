FROM python:3.12-slim

# Không cần venv trong container cho đỡ rối
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Cài thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Chạy FastAPI bằng uvicorn, không dùng "fastapi run" nữa
CMD ["uvicorn", "webapp_main:app", "--host", "0.0.0.0", "--port", "8000"]
