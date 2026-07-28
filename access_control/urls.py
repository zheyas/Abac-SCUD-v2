from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AccessEventViewSet,
    AccessGroupViewSet,
    AccessStatusView,
    AccessUserViewSet,
    BuildingViewSet,
    EntryAttemptView,
    HealthView,
    LoginView,
    LogoutView,
    PolicyViewSet,
    ToggleShiftView,
    UserStatusView,
    WeatherView,
)


router = DefaultRouter(trailing_slash=False)
router.register("buildings", BuildingViewSet, basename="building")
router.register("users", AccessUserViewSet, basename="user")
router.register("groups", AccessGroupViewSet, basename="group")
router.register("policies", PolicyViewSet, basename="policy")
router.register("access_events", AccessEventViewSet, basename="access-event")

admin_buildings = BuildingViewSet.as_view({"post": "create"})
admin_building_detail = BuildingViewSet.as_view({"put": "update", "delete": "destroy"})
admin_users = AccessUserViewSet.as_view({"post": "create"})
admin_user_detail = AccessUserViewSet.as_view({"put": "update", "delete": "destroy"})
admin_groups = AccessGroupViewSet.as_view({"post": "create"})
admin_group_detail = AccessGroupViewSet.as_view({"put": "update", "delete": "destroy"})
admin_group_members = AccessGroupViewSet.as_view({"post": "add_member"})
admin_policies = PolicyViewSet.as_view({"post": "create"})
admin_policy_detail = PolicyViewSet.as_view({"put": "update", "delete": "destroy"})

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("weather", WeatherView.as_view(), name="weather"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("access_status", AccessStatusView.as_view(), name="access-status"),
    path("toggle_shift", ToggleShiftView.as_view(), name="toggle-shift"),
    path("user_status", UserStatusView.as_view(), name="user-status"),
    path("entry_attempt", EntryAttemptView.as_view(), name="entry-attempt"),
    path("admin/buildings", admin_buildings, name="admin-buildings"),
    path("admin/buildings/<int:pk>", admin_building_detail, name="admin-building-detail"),
    path("admin/users", admin_users, name="admin-users"),
    path("admin/users/<int:pk>", admin_user_detail, name="admin-user-detail"),
    path("admin/groups", admin_groups, name="admin-groups"),
    path("admin/groups/<int:pk>", admin_group_detail, name="admin-group-detail"),
    path("admin/groups/<int:pk>/members", admin_group_members, name="admin-group-members"),
    path("admin/policies", admin_policies, name="admin-policies"),
    path("admin/policies/<int:pk>", admin_policy_detail, name="admin-policy-detail"),
] + router.urls
