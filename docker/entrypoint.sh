#!/bin/sh
set -e

# Встроенный PostgreSQL:
#   EMBEDDED_POSTGRES=1    — всегда поднимать Postgres внутри контейнера;
#   EMBEDDED_POSTGRES=0    — никогда (база снаружи: docker-compose, DATABASE_URL);
#   EMBEDDED_POSTGRES=auto — (по умолчанию) поднимать, если не задан DATABASE_URL
#                            и POSTGRES_HOST не указывает на другой хост.
EMBEDDED="${EMBEDDED_POSTGRES:-auto}"
if [ "$EMBEDDED" = "auto" ]; then
    case "${POSTGRES_HOST:-127.0.0.1}" in
        127.0.0.1|localhost) [ -z "$DATABASE_URL" ] && EMBEDDED=1 || EMBEDDED=0 ;;
        *) EMBEDDED=0 ;;
    esac
fi

if [ "$EMBEDDED" = "1" ]; then
    /app/docker/start-postgres.sh
    unset DATABASE_URL
    export POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432
fi

# Ждём, пока база данных начнёт принимать подключения
python - <<'PY'
import os, sys, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for attempt in range(1, 31):
    try:
        connection.ensure_connection()
        print("База данных доступна.")
        break
    except OperationalError as exc:
        print(f"Ожидание базы данных ({attempt}/30): {exc}".strip())
        time.sleep(2)
else:
    sys.exit("База данных так и не стала доступна.")
PY

python manage.py migrate --noinput
python manage.py seed_if_empty
python manage.py collectstatic --noinput --verbosity 0

exec "$@"
