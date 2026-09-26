#!/bin/sh
# Поднимает PostgreSQL внутри этого же контейнера (для Render и других
# платформ, где запускается один контейнер без docker-compose).
set -e

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PGBIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -n 1)"
DB_NAME="${POSTGRES_DB:-abac_scud}"
DB_USER="${POSTGRES_USER:-abac_scud}"
DB_PASSWORD="${POSTGRES_PASSWORD:-abac_scud}"

mkdir -p "$PGDATA" /var/run/postgresql
chown -R postgres:postgres "$PGDATA" /var/run/postgresql
chmod 700 "$PGDATA"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "[postgres] Инициализация кластера в $PGDATA"
    runuser -u postgres -- "$PGBIN/initdb" -D "$PGDATA" -U postgres \
        --auth-local=trust --auth-host=scram-sha-256 -E UTF8 --locale=C.UTF-8 >/dev/null
fi

echo "[postgres] Запуск сервера"
runuser -u postgres -- "$PGBIN/pg_ctl" -D "$PGDATA" -w -t 60 \
    -l /var/run/postgresql/server.log \
    -o "-c listen_addresses=127.0.0.1 -c port=5432 -c shared_buffers=32MB -c max_connections=30" start

psql_admin() {
    runuser -u postgres -- psql -h /var/run/postgresql -U postgres -v ON_ERROR_STOP=1 -tAq "$@"
}

if [ "$(psql_admin -c "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'")" != "1" ]; then
    echo "[postgres] Создаю пользователя $DB_USER"
    psql_admin -c "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$DB_PASSWORD'"
else
    psql_admin -c "ALTER ROLE \"$DB_USER\" PASSWORD '$DB_PASSWORD'"
fi

if [ "$(psql_admin -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")" != "1" ]; then
    echo "[postgres] Создаю базу $DB_NAME"
    psql_admin -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\""
fi

echo "[postgres] Готово: база $DB_NAME на 127.0.0.1:5432"
