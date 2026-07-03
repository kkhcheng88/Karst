# Karst dashboard — thin read-only web + daily scan. Deploy to Zeabur/any VPS.
FROM python:3.12-slim

# UTF-8 everywhere (defeatbeta prints an emoji banner that crashes non-UTF locales);
# defeatbeta-first so Yahoo's datacenter-IP throttling doesn't break the headless scan.
ENV PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KARST_DATA_SOURCE=defeatbeta \
    KARST_INPROC_CRON=1 \
    KARST_REFRESH_HOUR=9 \
    PORT=8000

WORKDIR /app

# deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code + small state files (the 200MB caches are excluded via .dockerignore)
COPY backtest/ ./backtest/
COPY thesis/ ./thesis/
COPY web/ ./web/

RUN mkdir -p web/data

EXPOSE 8000

# 1 worker (personal dashboard + the in-process scheduler must be a singleton);
# the scan runs off the request path so requests stay fast.
CMD ["gunicorn", "--chdir", "web", "app:app", \
     "--workers", "1", "--threads", "4", "--timeout", "120", \
     "--bind", "0.0.0.0:8000"]
