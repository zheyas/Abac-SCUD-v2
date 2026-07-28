from django.contrib import admin

from .models import AccessEvent, AccessGroup, AccessUser, Building, Policy, UserBuildingAccess


@admin.register(AccessGroup)
class AccessGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_accessible_to_all", "open_days", "open_time", "close_time", "is_24_hours")
    search_fields = ("name",)


@admin.register(AccessUser)
class AccessUserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "group", "is_active", "shift_status", "shift_auto")
    list_filter = ("group", "is_active", "shift_status", "shift_auto")
    search_fields = ("username",)


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "group", "user", "building", "effect", "is_active")
    list_filter = ("effect", "is_active", "requires_shift_active", "group", "building")
    search_fields = ("name",)


@admin.register(UserBuildingAccess)
class UserBuildingAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "building", "granted_at")


@admin.register(AccessEvent)
class AccessEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "building", "result", "reason", "context_time", "attempted_at")
    list_filter = ("result", "source", "building")
    search_fields = ("user__username", "building__name", "reason", "rule_name")
