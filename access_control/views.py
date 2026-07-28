from django.db.models import Count, Q
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AccessEvent, AccessGroup, AccessUser, Building, Policy
from .serializers import (
    AccessEventSerializer,
    AccessGroupSerializer,
    AccessStatusRequestSerializer,
    AccessUserSerializer,
    BuildingSerializer,
    EntryAttemptSerializer,
    LoginSerializer,
    PolicySerializer,
)
from .services import evaluate_access, get_effective_shift_status, parse_context_datetime


def session_user(request):
    user_id = request.session.get("scud_user_id")
    if not user_id:
        return None
    return AccessUser.objects.select_related("group").filter(pk=user_id).first()


def is_scud_admin(request):
    user = session_user(request)
    return bool(user and user.is_active and (user.group_id == 1 or user.group.name == "Администратор"))


class ScudAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_scud_admin(request)


def shift_payload(user, context_datetime=None):
    return {
        "shift_status": get_effective_shift_status(user, context_datetime),
        "shift_auto": user.shift_auto,
        "shift_days": user.shift_days,
        "shift_start": user.shift_start.strftime("%H:%M"),
        "shift_end": user.shift_end.strftime("%H:%M"),
    }


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok", "database": settings.DATABASES["default"]["ENGINE"]})


class WeatherView(APIView):
    def get(self, request):
        return Response(
            {
                "available": False,
                "error": "Погодный сервис не подключен в DRF-версии",
            },
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]
        user = AccessUser.objects.select_related("group").filter(username=username, is_active=True).first()
        if not user or not user.check_password(password):
            return Response({"success": False, "error": "Неверный логин или пароль"}, status=400)
        request.session["scud_user_id"] = user.id
        return Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "group_name": user.group.name,
                    "group_id": user.group_id,
                    "role_name": user.group.name,
                    "role_id": user.group_id,
                    **shift_payload(user),
                },
            }
        )


class LogoutView(APIView):
    def get(self, request):
        request.session.flush()
        return Response({"success": True})

    def post(self, request):
        request.session.flush()
        return Response({"success": True})


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [ScudAdminOrReadOnly]


class AccessUserViewSet(viewsets.ModelViewSet):
    queryset = AccessUser.objects.select_related("group").prefetch_related("personal_buildings")
    serializer_class = AccessUserSerializer
    permission_classes = [ScudAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.username == "admin":
            return Response({"error": "Основного администратора нельзя удалить"}, status=409)
        return super().destroy(request, *args, **kwargs)


class AccessGroupViewSet(viewsets.ModelViewSet):
    serializer_class = AccessGroupSerializer
    permission_classes = [ScudAdminOrReadOnly]

    def get_queryset(self):
        return AccessGroup.objects.annotate(
            member_count=Count("users", distinct=True),
            access_count=Count(
                "policies__building",
                filter=Q(policies__user__isnull=True, policies__is_active=True, policies__effect=Policy.EFFECT_ALLOW),
                distinct=True,
            ),
        )

    def perform_create(self, serializer):
        building_ids = serializer.validated_data.pop("building_ids", [])
        group = serializer.save()
        self._replace_group_access(group, building_ids)

    def perform_update(self, serializer):
        building_ids = serializer.validated_data.pop("building_ids", None)
        group = serializer.save()
        if building_ids is not None:
            self._replace_group_access(group, building_ids)

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if group.users.exists():
            return Response({"error": "Сначала перенесите пользователей в другую группу"}, status=409)
        return super().destroy(request, *args, **kwargs)

    @staticmethod
    def _replace_group_access(group, building_ids):
        Policy.objects.filter(group=group, user__isnull=True).delete()
        buildings = Building.objects.filter(pk__in=building_ids, is_accessible_to_all=False)
        Policy.objects.bulk_create(
            [
                Policy(
                    group=group,
                    building=building,
                    days_allowed="All",
                    time_start="00:00",
                    time_end="23:59",
                    requires_shift_active=True,
                    name=f"Группа {group.name}: {building.name}",
                    effect=Policy.EFFECT_ALLOW,
                    is_active=True,
                )
                for building in buildings
            ]
        )

    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "Выберите пользователя"}, status=400)
        user = get_object_or_404(AccessUser, pk=user_id)
        if user.username == "admin" and group.id != 1:
            return Response({"error": "Основного администратора нельзя перенести в другую группу"}, status=400)
        user.group = group
        user.save(update_fields=["group"])
        return Response({"success": True})


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.select_related("group", "user", "building")
    serializer_class = PolicySerializer
    permission_classes = [ScudAdminOrReadOnly]


class AccessEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccessEventSerializer

    def get_queryset(self):
        queryset = AccessEvent.objects.select_related("user", "building")
        if self.request.query_params.get("scope") != "all":
            user = session_user(self.request)
            if user:
                queryset = queryset.filter(user=user)
        limit = self.request.query_params.get("limit")
        if limit:
            try:
                return queryset[: max(1, min(int(limit), 200))]
            except ValueError:
                return queryset[:20]
        return queryset


class AccessStatusView(APIView):
    def post(self, request):
        serializer = AccessStatusRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(AccessUser.objects.select_related("group"), pk=serializer.validated_data["user_id"])
        context_datetime = parse_context_datetime(serializer.validated_data.get("timestamp"))
        buildings = Building.objects.all()
        decisions = {building.id: evaluate_access(user, building, context_datetime) for building in buildings}
        return Response({"buildings": decisions, "user": shift_payload(user, context_datetime)})


class ToggleShiftView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "no user"}, status=400)
        user = get_object_or_404(AccessUser, pk=user_id)
        if user.shift_auto:
            return Response({"error": "Смена управляется автоматически по расписанию"}, status=409)
        user.shift_status = AccessUser.SHIFT_INACTIVE if user.shift_status == AccessUser.SHIFT_ACTIVE else AccessUser.SHIFT_ACTIVE
        user.save(update_fields=["shift_status"])
        return Response({"shift_status": user.shift_status})


class UserStatusView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        user = get_object_or_404(AccessUser, pk=user_id)
        context_datetime = parse_context_datetime(request.data.get("timestamp"))
        return Response(shift_payload(user, context_datetime))


class EntryAttemptView(APIView):
    def post(self, request):
        serializer = EntryAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = request.session.get("scud_user_id") or serializer.validated_data.get("user_id")
        if not user_id:
            return Response({"error": "Требуется авторизация"}, status=401)
        user = get_object_or_404(AccessUser.objects.select_related("group"), pk=user_id)
        building = get_object_or_404(Building, pk=serializer.validated_data["building_id"])
        context_datetime = parse_context_datetime(serializer.validated_data.get("timestamp"))
        decision = evaluate_access(user, building, context_datetime)
        event = AccessEvent.objects.create(
            user=user,
            building=building,
            context_time=context_datetime,
            result=AccessEvent.RESULT_GRANTED if decision["access"] else AccessEvent.RESULT_DENIED,
            reason=decision["reason"],
            rule_name=decision.get("rule_name"),
            source=decision.get("source"),
        )
        return Response(
            {
                "success": True,
                "event_id": event.id,
                "building_name": building.name,
                "username": user.username,
                **decision,
            }
        )
