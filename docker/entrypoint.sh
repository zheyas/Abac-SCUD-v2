#!/bin/sh
set -e

# Ждём, пока база данных начнёт принимать подключения
python - <<'PY'
import os, sys, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for attempt in range(1, 61):
    try:
        connection.ensure_connection()
        print("База данных доступна.")
        break
    except OperationalError as exc:
        print(f"Ожидание базы данных ({attempt}/60): {exc}".strip())
        time.sleep(2)
else:
    sys.exit("База данных так и не стала доступна.")
PY

python manage.py migrate --noinput
python manage.py seed_if_empty
python manage.py collectstatic --noinput --verbosity 0

exec "$@"
