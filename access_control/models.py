import datetime

import bcrypt
from django.db import models


class AccessGroup(models.Model):
    """Access group. Kept close to the old Flask `roles` table semantics."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "roles"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Building(models.Model):
    name = models.CharField(max_length=160, unique=True)
    color_hex = models.CharField(max_length=16, default="#888")
    x = models.IntegerField(default=200)
    y = models.IntegerField(default=200)
    w = models.IntegerField(default=120)
    h = models.IntegerField(default=90)
    depth = models.IntegerField(default=30)
    is_accessible_to_all = models.BooleanField(default=False)
    open_days = models.CharField(max_length=64, default="Mon,Tue,Wed,Thu,Fri")
    open_time = models.TimeField(default=datetime.time(8, 0))
    close_time = models.TimeField(default=datetime.time(20, 0))
    is_24_hours = models.BooleanField(default=False)

    class Meta:
        db_table = "buildings"
        ordering = ["id"]

    def __str__(self):
        return self.name


class AccessUser(models.Model):
    SHIFT_ACTIVE = "active"
    SHIFT_INACTIVE = "inactive"
    SHIFT_CHOICES = (
        (SHIFT_ACTIVE, "Активна"),
        (SHIFT_INACTIVE, "Неактивна"),
    )

    username = models.CharField(max_length=120, unique=True)
    password_hash = models.CharField(max_length=255)
    group = models.ForeignKey(AccessGroup, on_delete=models.PROTECT, related_name="users")
    is_active = models.BooleanField(default=True)
    shift_status = models.CharField(max_length=16, choices=SHIFT_CHOICES, default=SHIFT_INACTIVE)
    shift_auto = models.BooleanField(default=False)
    shift_days = models.CharField(max_length=64, default="Mon,Tue,Wed,Thu,Fri")
    shift_start = models.TimeField(default=datetime.time(8, 0))
    shift_end = models.TimeField(default=datetime.time(18, 0))
    personal_buildings = models.ManyToManyField(
        Building,
        through="UserBuildingAccess",
        related_name="personal_users",
        blank=True,
    )

    class Meta:
        db_table = "users"
        ordering = ["id"]

    def __str__(self):
        return self.username

    def set_password(self, raw_password):
        raw_password = raw_password or ""
        self.password_hash = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return bcrypt.checkpw((raw_password or "").encode(), self.password_hash.encode())


class UserBuildingAccess(models.Model):
    user = models.ForeignKey(AccessUser, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_building_access"
        constraints = [
            models.UniqueConstraint(fields=["user", "building"], name="uniq_user_building_access")
        ]
        ordering = ["building_id"]


class Policy(models.Model):
    EFFECT_ALLOW = "allow"
    EFFECT_DENY = "deny"
    EFFECT_CHOICES = (
        (EFFECT_ALLOW, "Разрешить"),
        (EFFECT_DENY, "Запретить"),
    )

    group = models.ForeignKey(AccessGroup, on_delete=models.CASCADE, related_name="policies")
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="policies")
    user = models.ForeignKey(
        AccessUser,
        on_delete=models.CASCADE,
        related_name="personal_policies",
        null=True,
        blank=True,
    )
    days_allowed = models.CharField(max_length=64, default="Mon,Tue,Wed,Thu,Fri")
    time_start = models.TimeField(default=datetime.time(8, 0))
    time_end = models.TimeField(default=datetime.time(18, 0))
    requires_shift_active = models.BooleanField(default=True)
    name = models.CharField(max_length=255, blank=True, default="")
    effect = models.CharField(max_length=16, choices=EFFECT_CHOICES, default=EFFECT_ALLOW)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "policies"
        ordering = ["-user_id", "id"]
        indexes = [
            models.Index(fields=["user", "building"], name="idx_policy_user_building"),
            models.Index(fields=["group", "building"], name="idx_policy_group_building"),
        ]

    def __str__(self):
        return self.name or f"Policy #{self.pk}"


class AccessEvent(models.Model):
    RESULT_GRANTED = "granted"
    RESULT_DENIED = "denied"
    RESULT_CHOICES = (
        (RESULT_GRANTED, "Разрешено"),
        (RESULT_DENIED, "Отклонено"),
    )

    user = models.ForeignKey(AccessUser, on_delete=models.CASCADE, related_name="access_events")
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="access_events")
    attempted_at = models.DateTimeField(auto_now_add=True)
    context_time = models.DateTimeField()
    result = models.CharField(max_length=16, choices=RESULT_CHOICES)
    reason = models.CharField(max_length=255)
    rule_name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = "access_events"
        ordering = ["-id"]
        indexes = [models.Index(fields=["-attempted_at"], name="idx_access_events_time")]


class AppMeta(models.Model):
    key = models.CharField(max_length=120, primary_key=True)
    value = models.CharField(max_length=255)

    class Meta:
        db_table = "app_meta"
