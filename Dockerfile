FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PGDATA=/var/lib/postgresql/data

# PostgreSQL внутри контейнера (используется, когда внешняя БД не задана — например, на Render).
# Кластер по умолчанию не создаём: его инициализирует docker/start-postgres.sh в $PGDATA.
RUN mkdir -p /etc/postgresql-common \
    && echo "create_main_cluster = false" > /etc/postgresql-common/createcluster.conf \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker/*.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
# Render передаёт порт в переменной PORT; локально по умолчанию 8000
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --access-logfile -"]
