import datetime

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AccessGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "roles", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="Building",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True)),
                ("color_hex", models.CharField(default="#888", max_length=16)),
                ("x", models.IntegerField(default=200)),
                ("y", models.IntegerField(default=200)),
                ("w", models.IntegerField(default=120)),
                ("h", models.IntegerField(default=90)),
                ("depth", models.IntegerField(default=30)),
                ("is_accessible_to_all", models.BooleanField(default=False)),
                ("open_days", models.CharField(default="Mon,Tue,Wed,Thu,Fri", max_length=64)),
                ("open_time", models.TimeField(default=datetime.time(8, 0))),
                ("close_time", models.TimeField(default=datetime.time(20, 0))),
                ("is_24_hours", models.BooleanField(default=False)),
            ],
            options={"db_table": "buildings", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="AppMeta",
            fields=[
                ("key", models.CharField(max_length=120, primary_key=True, serialize=False)),
                ("value", models.CharField(max_length=255)),
            ],
            options={"db_table": "app_meta"},
        ),
        migrations.CreateModel(
            name="AccessUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(max_length=120, unique=True)),
                ("password_hash", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "shift_status",
                    models.CharField(
                        choices=[("active", "Активна"), ("inactive", "Неактивна")],
                        default="inactive",
                        max_length=16,
                    ),
                ),
                ("shift_auto", models.BooleanField(default=False)),
                ("shift_days", models.CharField(default="Mon,Tue,Wed,Thu,Fri", max_length=64)),
                ("shift_start", models.TimeField(default=datetime.time(8, 0))),
                ("shift_end", models.TimeField(default=datetime.time(18, 0))),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="users",
                        to="access_control.accessgroup",
                    ),
                ),
            ],
            options={"db_table": "users", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="UserBuildingAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "building",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="access_control.building"),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="access_control.accessuser")),
            ],
            options={"db_table": "user_building_access", "ordering": ["building_id"]},
        ),
        migrations.AddField(
            model_name="accessuser",
            name="personal_buildings",
            field=models.ManyToManyField(
                blank=True,
                related_name="personal_users",
                through="access_control.UserBuildingAccess",
                to="access_control.building",
            ),
        ),
        migrations.CreateModel(
            name="Policy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("days_allowed", models.CharField(default="Mon,Tue,Wed,Thu,Fri", max_length=64)),
                ("time_start", models.TimeField(default=datetime.time(8, 0))),
                ("time_end", models.TimeField(default=datetime.time(18, 0))),
                ("requires_shift_active", models.BooleanField(default=True)),
                ("name", models.CharField(blank=True, default="", max_length=255)),
                (
                    "effect",
                    models.CharField(
                        choices=[("allow", "Разрешить"), ("deny", "Запретить")],
                        default="allow",
                        max_length=16,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="policies",
                        to="access_control.building",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="policies",
                        to="access_control.accessgroup",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="personal_policies",
                        to="access_control.accessuser",
                    ),
                ),
            ],
            options={"db_table": "policies", "ordering": ["-user_id", "id"]},
        ),
        migrations.CreateModel(
            name="AccessEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("context_time", models.DateTimeField()),
                (
                    "result",
                    models.CharField(
                        choices=[("granted", "Разрешено"), ("denied", "Отклонено")],
                        max_length=16,
                    ),
                ),
                ("reason", models.CharField(max_length=255)),
                ("rule_name", models.CharField(blank=True, max_length=255, null=True)),
                ("source", models.CharField(blank=True, max_length=64, null=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_events",
                        to="access_control.building",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_events",
                        to="access_control.accessuser",
                    ),
                ),
            ],
            options={"db_table": "access_events", "ordering": ["-id"]},
        ),
        migrations.AddConstraint(
            model_name="userbuildingaccess",
            constraint=models.UniqueConstraint(fields=("user", "building"), name="uniq_user_building_access"),
        ),
        migrations.AddIndex(
            model_name="policy",
            index=models.Index(fields=["user", "building"], name="idx_policy_user_building"),
        ),
        migrations.AddIndex(
            model_name="policy",
            index=models.Index(fields=["group", "building"], name="idx_policy_group_building"),
        ),
        migrations.AddIndex(
            model_name="accessevent",
            index=models.Index(fields=["-attempted_at"], name="idx_access_events_time"),
        ),
    ]
