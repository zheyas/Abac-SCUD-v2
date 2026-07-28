import datetime

from django.test import TestCase

from .models import AccessGroup, AccessUser, Building, Policy
from .services import evaluate_access


class AccessEngineTests(TestCase):
    def setUp(self):
        self.group = AccessGroup.objects.create(name="Стажёры")
        self.user = AccessUser.objects.create(
            username="zheyas",
            password_hash="unused",
            group=self.group,
            is_active=True,
            shift_auto=True,
            shift_days="All",
            shift_start=datetime.time(8, 0),
            shift_end=datetime.time(13, 30),
        )
        self.administration = Building.objects.create(
            name="Администрация",
            open_days="All",
            open_time=datetime.time(8, 0),
            close_time=datetime.time(19, 0),
            is_accessible_to_all=False,
        )
        self.annex = Building.objects.create(
            name="Пристройка",
            open_days="All",
            open_time=datetime.time(7, 0),
            close_time=datetime.time(20, 0),
            is_accessible_to_all=False,
        )
        Policy.objects.create(
            group=self.group,
            building=self.annex,
            days_allowed="All",
            time_start=datetime.time(0, 0),
            time_end=datetime.time(23, 59),
            requires_shift_active=True,
        )
        self.user.personal_buildings.add(self.annex)

    @staticmethod
    def moment(hour, minute):
        return datetime.datetime(2026, 6, 23, hour, minute, tzinfo=datetime.timezone.utc)

    def test_group_does_not_grant_unselected_building(self):
        decision = evaluate_access(self.user, self.administration, self.moment(12, 0))
        self.assertFalse(decision["access"])

    def test_personal_access_stops_exactly_at_shift_end(self):
        before = evaluate_access(self.user, self.annex, self.moment(13, 29))
        at_end = evaluate_access(self.user, self.annex, self.moment(13, 30))

        self.assertTrue(before["access"])
        self.assertFalse(at_end["access"])
        self.assertEqual(at_end["reason"], "Смена не активна")

    def test_building_closes_exactly_at_end_time(self):
        self.user.shift_end = datetime.time(21, 0)
        decision = evaluate_access(self.user, self.annex, self.moment(20, 0))

        self.assertFalse(decision["access"])
        self.assertEqual(decision["status"], "closed")
