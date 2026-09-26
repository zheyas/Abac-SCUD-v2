from django.core.management import call_command
from django.core.management.base import BaseCommand

from access_control.models import AccessGroup, AccessUser, Building, Policy


class Command(BaseCommand):
    help = "Заполняет базу демо-данными (seed_demo), только если она пустая."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Запустить seed_demo даже если данные уже есть (команда идемпотентна).",
        )

    def handle(self, *args, **options):
        counts = {
            model.__name__: model.objects.count()
            for model in (AccessUser, AccessGroup, Building, Policy)
        }
        if any(counts.values()) and not options["force"]:
            summary = ", ".join(f"{name}={count}" for name, count in counts.items())
            self.stdout.write(f"База уже содержит данные ({summary}) — заполнение пропущено.")
            return

        self.stdout.write("База пустая — заполняю демо-данными...")
        call_command("seed_demo")
