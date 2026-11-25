FROM python:3.12-slim

WORKDIR /app

# No .pyc files and logs straight to stdout.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HOST=0.0.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY web/ web/

EXPOSE 5000
CMD ["python", "-m", "pyngo.app"]
