# Raven-Eye — single image (dashboard + Telegram bot + Chromium)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# System libs needed by Chromium (Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt \
 && python -m playwright install --with-deps chromium

COPY . .

RUN chmod +x start.sh docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["bash", "start.sh"]
