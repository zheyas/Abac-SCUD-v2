FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
# Render передаёт порт в переменной PORT; локально по умолчанию 8000
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --access-logfile -"]
