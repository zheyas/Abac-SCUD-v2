import datetime

from django.utils import timezone

from .models import AccessUser, Building, Policy


def day_allowed(days_value, day_name):
    days = [day.strip() for day in (days_value or "").split(",") if day.strip()]
    return "All" in days or day_name in days


def get_effective_shift_status(user, context_datetime=None):
    if not user.shift_auto:
        return user.shift_status

    now = context_datetime or timezone.localtime()
    days_value = user.shift_days or ""
    current = now.time().replace(tzinfo=None)
    start = user.shift_start
    end = user.shift_end

    if start <= end:
        active = day_allowed(days_value, now.strftime("%a")) and start <= current < end
    elif current >= start:
        active = day_allowed(days_value, now.strftime("%a"))
    elif current < end:
        previous_day = (now - datetime.timedelta(days=1)).strftime("%a")
        active = day_allowed(days_value, previous_day)
    else:
        active = False
    return AccessUser.SHIFT_ACTIVE if active else AccessUser.SHIFT_INACTIVE


def is_building_open(building, context_datetime=None):
    now = context_datetime or timezone.localtime()
    if building.is_24_hours:
        return day_allowed(building.open_days, now.strftime("%a"))

    current = now.time().replace(tzinfo=None)
    opening = building.open_time
    closing = building.close_time

    if opening <= closing:
        return day_allowed(building.open_days, now.strftime("%a")) and opening <= current < closing

    if current >= opening:
        return day_allowed(building.open_days, now.strftime("%a"))
    if current < closing:
        previous_day = (now - datetime.timedelta(days=1)).strftime("%a")
        return day_allowed(building.open_days, previous_day)
    return False


def building_schedule_label(building):
    if building.is_24_hours:
        return "Круглосуточно"
    return f"{building.open_time.strftime('%H:%M')}–{building.close_time.strftime('%H:%M')}"


def evaluate_access(user, building, context_datetime=None):
    now = context_datetime or timezone.localtime()
    schedule = building_schedule_label(building)
    building_open = is_building_open(building, now)

    if not building_open:
        return {
            "access": False,
            "building_open": False,
            "status": "closed",
            "reason": "Закрыто по графику",
            "schedule": schedule,
            "source": "building",
            "rule_id": None,
            "rule_name": None,
        }
    if not user.is_active:
        return {
            "access": False,
            "building_open": True,
            "status": "denied",
            "reason": "Учётная запись заблокирована",
            "schedule": schedule,
            "source": "account",
            "rule_id": None,
            "rule_name": None,
        }
    if building.is_accessible_to_all:
        return {
            "access": True,
            "building_open": True,
            "status": "available",
            "reason": "Общий доступ",
            "schedule": schedule,
            "source": "building",
            "rule_id": None,
            "rule_name": "Общий доступ",
        }

    effective_shift = get_effective_shift_status(user, now)
    if effective_shift != AccessUser.SHIFT_ACTIVE:
        return {
            "access": False,
            "building_open": True,
            "status": "denied",
            "reason": "Смена не активна",
            "schedule": schedule,
            "source": "shift",
            "rule_id": None,
            "rule_name": None,
        }

    policies = (
        Policy.objects.filter(building=building, is_active=True)
        .filter(user=user)
        | Policy.objects.filter(building=building, is_active=True, user__isnull=True, group=user.group)
    )
    policies = policies.select_related("group", "building", "user").order_by(
        "-user_id", "effect", "id"
    )

    shift_blocked = False
    schedule_blocked = False
    current_time = now.time().replace(tzinfo=None)
    current_day = now.strftime("%a")
    matching_personal = []
    matching_group = []

    for policy in policies:
        if policy.requires_shift_active and effective_shift != AccessUser.SHIFT_ACTIVE:
            shift_blocked = True
            continue
        if not day_allowed(policy.days_allowed, current_day):
            schedule_blocked = True
            continue
        start = policy.time_start
        end = policy.time_end
        within_window = start <= current_time < end if start <= end else current_time >= start or current_time < end
        if within_window:
            (matching_personal if policy.user_id else matching_group).append(policy)
            continue
        schedule_blocked = True

    def decision_from_rules(rules, source):
        if not rules:
            return None
        rule = next((item for item in rules if item.effect == Policy.EFFECT_DENY), rules[0])
        allowed = rule.effect != Policy.EFFECT_DENY
        return {
            "access": allowed,
            "building_open": True,
            "status": "available" if allowed else "denied",
            "reason": "Разрешено персональным правилом"
            if allowed and source == "user"
            else "Запрещено персональным правилом"
            if source == "user"
            else "Разрешено правилом группы"
            if allowed
            else "Запрещено правилом группы",
            "schedule": schedule,
            "source": source,
            "rule_id": rule.id,
            "rule_name": rule.name or f"Правило #{rule.id}",
        }

    personal_decision = decision_from_rules(matching_personal, "user")
    if personal_decision:
        return personal_decision

    if user.personal_buildings.filter(pk=building.pk).exists():
        return {
            "access": True,
            "building_open": True,
            "status": "available",
            "reason": "Персональный доступ из карточки",
            "schedule": schedule,
            "source": "user_card",
            "rule_id": None,
            "rule_name": "Личный допуск",
        }

    group_decision = decision_from_rules(matching_group, "group")
    if group_decision:
        return group_decision

    if shift_blocked:
        reason = "Требуется активная смена"
    elif schedule_blocked:
        reason = "Вне времени политики"
    else:
        reason = "Нет подходящей политики"
    return {
        "access": False,
        "building_open": True,
        "status": "denied",
        "reason": reason,
        "schedule": schedule,
        "source": "policy",
        "rule_id": None,
        "rule_name": None,
    }


def parse_context_datetime(value=None):
    if not value:
        return timezone.localtime()
    parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return timezone.localtime(parsed)
