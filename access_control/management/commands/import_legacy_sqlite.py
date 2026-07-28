import datetime
import shutil
import sqlite3
import tempfile
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils import timezone

from access_control.models import (
    AccessEvent,
    AccessGroup,
    AccessUser,
    AppMeta,
    Building,
    Policy,
    UserBuildingAccess,
)


class Command(BaseCommand):
    help = "Import data from the legacy Flask/SQLite ABAC SCUD database."

    def add_arguments(self, parser):
        parser.add_argument(
            "sqlite_path",
            nargs="?",
            default="/Users/evgenijasakov/НИР/abac_scud.db",
            help="Path to legacy abac_scud.db",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        sqlite_path = Path(options["sqlite_path"]).expanduser()
        if not sqlite_path.exists():
            raise CommandError(f"SQLite database not found: {sqlite_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "legacy_abac_scud.db"
            shutil.copyfile(sqlite_path, temp_db)
            source = sqlite3.connect(str(temp_db))
            source.row_factory = sqlite3.Row

            self._import_groups(source)
            self._import_buildings(source)
            self._import_users(source)
            self._import_policies(source)
            self._import_personal_access(source)
            self._import_access_events(source)
            self._import_app_meta(source)
            source.close()
        self._reset_sequences()

        self.stdout.write(self.style.SUCCESS(f"Imported legacy data from {sqlite_path}"))

    @staticmethod
    def _rows(source, table):
        return source.execute(f"SELECT * FROM {table}").fetchall()

    def _import_groups(self, source):
        for row in self._rows(source, "roles"):
            AccessGroup.objects.update_or_create(
                id=row["id"],
                defaults={
                    "name": row["name"],
                    "description": row["description"] if "description" in row.keys() else "",
                },
            )

    def _import_buildings(self, source):
        for row in self._rows(source, "buildings"):
            Building.objects.update_or_create(
                id=row["id"],
                defaults={
                    "name": row["name"],
                    "color_hex": row["color_hex"],
                    "x": row["x"],
                    "y": row["y"],
                    "w": row["w"],
                    "h": row["h"],
                    "depth": row["depth"],
                    "is_accessible_to_all": bool(row["is_accessible_to_all"]),
                    "open_days": row["open_days"],
                    "open_time": _time(row["open_time"]),
                    "close_time": _time(row["close_time"]),
                    "is_24_hours": bool(row["is_24_hours"]),
                },
            )

    def _import_users(self, source):
        for row in self._rows(source, "users"):
            AccessUser.objects.update_or_create(
                id=row["id"],
                defaults={
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "group_id": row["role_id"],
                    "is_active": bool(row["is_active"]),
                    "shift_status": row["shift_status"],
                    "shift_auto": bool(row["shift_auto"]) if "shift_auto" in row.keys() else False,
                    "shift_days": row["shift_days"] if "shift_days" in row.keys() else "Mon,Tue,Wed,Thu,Fri",
                    "shift_start": _time(row["shift_start"] if "shift_start" in row.keys() else "08:00"),
                    "shift_end": _time(row["shift_end"] if "shift_end" in row.keys() else "18:00"),
                },
            )

    def _import_policies(self, source):
        for row in self._rows(source, "policies"):
            Policy.objects.update_or_create(
                id=row["id"],
                defaults={
                    "group_id": row["role_id"],
                    "building_id": row["building_id"],
                    "user_id": row["user_id"] if "user_id" in row.keys() else None,
                    "days_allowed": row["days_allowed"],
                    "time_start": _time(row["time_start"]),
                    "time_end": _time(row["time_end"]),
                    "requires_shift_active": bool(row["requires_shift_active"]),
                    "name": row["name"] if "name" in row.keys() else "",
                    "effect": row["effect"] if "effect" in row.keys() else Policy.EFFECT_ALLOW,
                    "is_active": bool(row["is_active"]) if "is_active" in row.keys() else True,
                },
            )

    def _import_personal_access(self, source):
        UserBuildingAccess.objects.all().delete()
        for row in self._rows(source, "user_building_access"):
            UserBuildingAccess.objects.get_or_create(user_id=row["user_id"], building_id=row["building_id"])

    def _import_access_events(self, source):
        for row in self._rows(source, "access_events"):
            AccessEvent.objects.update_or_create(
                id=row["id"],
                defaults={
                    "user_id": row["user_id"],
                    "building_id": row["building_id"],
                    "context_time": _datetime(row["context_time"]),
                    "result": row["result"],
                    "reason": row["reason"],
                    "rule_name": row["rule_name"],
                    "source": row["source"],
                    "attempted_at": _datetime(row["attempted_at"]),
                },
            )

    def _import_app_meta(self, source):
        for row in self._rows(source, "app_meta"):
            AppMeta.objects.update_or_create(key=row["key"], defaults={"value": row["value"]})

    @staticmethod
    def _reset_sequences():
        models = [
            apps.get_model("access_control", model_name)
            for model_name in ["AccessGroup", "Building", "AccessUser", "Policy", "AccessEvent", "UserBuildingAccess"]
        ]
        statements = connection.ops.sequence_reset_sql(no_style(), models)
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)


def _time(value):
    if isinstance(value, datetime.time):
        return value
    hour, minute = [int(part) for part in str(value or "00:00").split(":", 1)]
    return datetime.time(hour, minute)


def _datetime(value):
    if isinstance(value, datetime.datetime):
        parsed = value
    else:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed
