import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from access_control.models import AccessGroup, AccessUser, Building, Policy


class Command(BaseCommand):
    help = "Create demo ABAC SCUD groups, users, buildings and access policies."

    @transaction.atomic
    def handle(self, *args, **options):
        groups = {}
        for name in ["Администратор", "Производство", "Охрана", "Инженер", "Гость", "Медслужба"]:
            groups[name], _ = AccessGroup.objects.get_or_create(name=name)

        building_specs = [
            ("Администрация", "#a55d35", 200, 200, 140, 100, 35, False, "Mon,Tue,Wed,Thu,Fri", "08:00", "19:00", False),
            ("Производство", "#7a8c8c", 450, 150, 180, 110, 40, False, "All", "06:00", "23:00", False),
            ("Столовая", "#6a9c78", 750, 250, 130, 90, 30, False, "All", "07:00", "22:00", False),
            ("Бункер", "#5a5e6b", 350, 400, 150, 80, 25, True, "All", "00:00", "23:59", True),
            ("Убежище", "#8b7a6b", 650, 380, 120, 70, 25, True, "All", "00:00", "23:59", True),
        ]
        buildings = {}
        for name, color, x, y, w, h, depth, is_all, days, opening, closing, around_clock in building_specs:
            building, _ = Building.objects.update_or_create(
                name=name,
                defaults={
                    "color_hex": color,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "depth": depth,
                    "is_accessible_to_all": is_all,
                    "open_days": days,
                    "open_time": _time(opening),
                    "close_time": _time(closing),
                    "is_24_hours": around_clock,
                },
            )
            buildings[name] = building

        users = [
            ("admin", "admin123", "Администратор", "active", False, "All", "00:00", "23:59"),
            ("worker", "prod123", "Производство", "inactive", True, "Mon,Tue,Wed,Thu,Fri", "07:00", "19:00"),
            ("guard", "guard123", "Охрана", "active", True, "All", "00:00", "23:59"),
            ("engineer", "engineer123", "Инженер", "active", True, "Mon,Tue,Wed,Thu,Fri,Sat", "07:00", "21:00"),
            ("medic", "medic123", "Медслужба", "inactive", False, "Mon,Tue,Wed,Thu,Fri", "08:00", "18:00"),
            ("guest", "guest123", "Гость", "inactive", False, "Mon,Tue,Wed,Thu,Fri", "08:00", "18:00"),
        ]
        for username, password, group_name, shift_status, shift_auto, shift_days, shift_start, shift_end in users:
            user, created = AccessUser.objects.get_or_create(
                username=username,
                defaults={
                    "group": groups[group_name],
                    "shift_status": shift_status,
                    "shift_auto": shift_auto,
                    "shift_days": shift_days,
                    "shift_start": _time(shift_start),
                    "shift_end": _time(shift_end),
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password_hash"])

        default_policies = [
            ("Администратор", "Администрация"),
            ("Администратор", "Производство"),
            ("Производство", "Производство"),
            ("Охрана", "Администрация"),
            ("Охрана", "Производство"),
            ("Инженер", "Производство"),
            ("Медслужба", "Администрация"),
            ("Медслужба", "Производство"),
        ]
        for group_name, building_name in default_policies:
            group = groups[group_name]
            building = buildings[building_name]
            Policy.objects.get_or_create(
                group=group,
                building=building,
                user=None,
                defaults={
                    "days_allowed": "All",
                    "time_start": _time("00:00"),
                    "time_end": _time("23:59"),
                    "requires_shift_active": True,
                    "name": f"Группа {group.name}: {building.name}",
                    "effect": Policy.EFFECT_ALLOW,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo ABAC SCUD data is ready."))


def _time(value):
    hour, minute = [int(part) for part in value.split(":", 1)]
    return datetime.time(hour, minute)
