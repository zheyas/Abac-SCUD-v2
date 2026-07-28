# ABAC SCUD API на Django REST Framework

Проект переносит Flask/SQLite-прототип СКУД в backend на Django REST Framework и PostgreSQL.

## Что внутри

- PostgreSQL-схема через Django models и migrations.
- DRF API для пользователей, групп доступа, зданий, политик и журнала проходов.
- ABAC-движок доступа как отдельный сервисный слой.
- Сессионный login/logout для демо-пользователей.
- Seed-команда с демонстрационными пользователями, зданиями и правилами.
- Тесты критичных правил доступа.

## Стек

- Python 3.11+
- Django 5.2
- Django REST Framework
- PostgreSQL
- psycopg 3
- bcrypt

## Быстрый запуск

### Через Docker Compose

Compose поднимает только Django-приложение. PostgreSQL должен быть запущен на Mac,
в уже созданной локальной базе `abac_scud`.

```bash
cp .env.example .env
docker compose up --build
```

3D-карта будет доступна на `http://127.0.0.1:8000/`, API — на `http://127.0.0.1:8000/api/`.

### Без Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8080
```

3D-карта будет доступна на `http://127.0.0.1:8080/`, API — на `http://127.0.0.1:8080/api/`.

## Демо-аккаунты

| Логин | Пароль | Группа |
|---|---|---|
| `admin` | `admin123` | Администратор |
| `worker` | `prod123` | Производство |
| `guard` | `guard123` | Охрана |
| `engineer` | `engineer123` | Инженер |
| `medic` | `medic123` | Медслужба |
| `guest` | `guest123` | Гость |

## Основные endpoints

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/health` | healthcheck |
| `POST` | `/api/login` | вход пользователя |
| `GET/POST` | `/api/logout` | выход |
| `GET/POST` | `/api/buildings` | список/создание зданий |
| `GET/POST` | `/api/users` | список/создание пользователей СКУД |
| `GET/POST` | `/api/groups` | группы доступа |
| `POST` | `/api/groups/<id>/members` | добавить пользователя в группу |
| `GET/POST` | `/api/policies` | политики доступа |
| `POST` | `/api/access_status` | рассчитать доступ пользователя ко всем объектам |
| `POST` | `/api/entry_attempt` | зарегистрировать попытку прохода |
| `GET` | `/api/access_events` | журнал попыток прохода |
| `POST` | `/api/toggle_shift` | переключить ручную смену |
| `POST` | `/api/user_status` | получить статус смены |

Для совместимости со старым frontend также оставлены write-маршруты вида `/api/admin/buildings`, `/api/admin/users`, `/api/admin/groups`, `/api/admin/policies`.

## Локальная проверка без PostgreSQL

Если нужно быстро прогнать тесты без поднятой БД:

```bash
SCUD_SQLITE=1 python manage.py test
```

## Миграция старой SQLite-базы

После `python manage.py migrate` можно импортировать данные из старого Flask/SQLite-проекта:

```bash
python manage.py import_legacy_sqlite /Users/evgenijasakov/НИР/abac_scud.db
```

Команда переносит таблицы `roles`, `users`, `buildings`, `policies`, `user_building_access`, `access_events`, `app_meta` в PostgreSQL.
