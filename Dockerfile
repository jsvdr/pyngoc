FROM python:3.12-slim

WORKDIR /app

# Sin .pyc y logs directos a stdout.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

EXPOSE 5000
CMD ["python", "backend/app.py"]
