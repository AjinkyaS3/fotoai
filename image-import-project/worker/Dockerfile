FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FIXED: Use "worker:app" to match your code
CMD ["celery", "-A", "worker:app", "worker", "--loglevel=info"]