import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils import timezone

from chores.models import ChoreAssignment
from chores.models import Roommate
from chores.models import Chore


class RootUrlPlaceholderTests(TestCase):
    """Placeholder for the scaffold; replaced by the dashboard test in #10."""

    def test_root_url_returns_404(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 404)


class RoommateModelTests(TestCase):
    def test_name_field_definition(self):
        field = Roommate._meta.get_field("name")

        self.assertEqual(field.max_length, 60)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)

    def test_total_points_field_definition_and_default(self):
        field = Roommate._meta.get_field("total_points")

        self.assertEqual(field.default, 0)
        roommate = Roommate.objects.create(name="Alex")
        roommate.refresh_from_db()
        self.assertEqual(roommate.total_points, 0)

    def test_created_at_is_auto_now_add(self):
        field = Roommate._meta.get_field("created_at")

        self.assertTrue(field.auto_now_add)
        roommate = Roommate.objects.create(name="Alex")
        roommate.refresh_from_db()
        self.assertIsNotNone(roommate.created_at)

    def test_str_returns_name(self):
        roommate = Roommate.objects.create(name="Alex")

        self.assertEqual(str(roommate), "Alex")

    def test_name_is_required(self):
        roommate = Roommate(name="")

        with self.assertRaises(ValidationError):
            roommate.full_clean()

    def test_name_longer_than_60_characters_fails_validation(self):
        roommate = Roommate(name="x" * 61)

        with self.assertRaises(ValidationError):
            roommate.full_clean()

    def test_name_of_exactly_60_characters_is_valid(self):
        roommate = Roommate(name="x" * 60)

        roommate.full_clean()

    def test_negative_total_points_are_accepted(self):
        roommate = Roommate.objects.create(name="Alex", total_points=-5)

        roommate.refresh_from_db()
        self.assertEqual(roommate.total_points, -5)

    def test_names_are_not_unique(self):
        first = Roommate.objects.create(name="Alex")
        second = Roommate.objects.create(name="Alex")

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(Roommate.objects.filter(name="Alex").count(), 2)


class ChoreModelTests(TestCase):
    def test_field_definitions(self):
        title = Chore._meta.get_field("title")
        description = Chore._meta.get_field("description")
        weight = Chore._meta.get_field("weight")
        recurrence_day = Chore._meta.get_field("recurrence_day")
        is_active = Chore._meta.get_field("is_active")

        self.assertEqual(title.max_length, 100)
        self.assertFalse(title.blank)
        self.assertFalse(title.unique)
        self.assertTrue(description.blank)
        self.assertEqual(weight.default, 1)
        self.assertEqual(recurrence_day.choices, Chore.DAYS_OF_WEEK)
        self.assertEqual(is_active.default, True)

    def test_days_of_week_are_monday_through_sunday(self):
        self.assertEqual(Chore.DAYS_OF_WEEK, [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])

    def test_defaults(self):
        chore = Chore.objects.create(title="Trash", recurrence_day=0)

        chore.refresh_from_db()
        self.assertEqual(chore.description, "")
        self.assertEqual(chore.weight, 1)
        self.assertTrue(chore.is_active)

    def test_create_with_only_a_title_uses_field_defaults(self):
        chore = Chore.objects.create(title="Trash")

        chore.refresh_from_db()
        self.assertEqual(chore.description, "")
        self.assertEqual(chore.weight, 1)
        self.assertEqual(chore.recurrence_day, 0)
        self.assertTrue(chore.is_active)

    def test_recurrence_day_accepts_all_days_of_week(self):
        for day, expected_name in Chore.DAYS_OF_WEEK:
            with self.subTest(day=expected_name):
                chore = Chore(title="Trash", recurrence_day=day)

                chore.full_clean()
                self.assertEqual(chore.recurrence_day, day)

    def test_invalid_recurrence_day_fails_full_clean(self):
        for recurrence_day in (-1, 7):
            with self.subTest(recurrence_day=recurrence_day):
                chore = Chore(title="Trash", recurrence_day=recurrence_day)

                with self.assertRaises(ValidationError):
                    chore.full_clean()

    def test_title_is_required(self):
        chore = Chore(title="", recurrence_day=0)

        with self.assertRaises(ValidationError):
            chore.full_clean()

    def test_title_longer_than_100_characters_fails_full_clean(self):
        chore = Chore(title="x" * 101, recurrence_day=0)

        with self.assertRaises(ValidationError):
            chore.full_clean()

    def test_titles_are_not_unique(self):
        Chore.objects.create(title="Trash", recurrence_day=0)
        Chore.objects.create(title="Trash", recurrence_day=0)

        self.assertEqual(Chore.objects.filter(title="Trash").count(), 2)

    def test_str_returns_title(self):
        chore = Chore.objects.create(title="Trash", recurrence_day=0)

        self.assertEqual(str(chore), "Trash")


class ChoreAssignmentModelTests(TestCase):
    def setUp(self):
        self.chore = Chore.objects.create(title="Trash", recurrence_day=0)
        self.roommate = Roommate.objects.create(name="Alex")
        self.due_date = datetime.date(2026, 9, 14)

    def create_assignment(self, **overrides):
        values = {
            "chore": self.chore,
            "assigned_to": self.roommate,
            "due_date": self.due_date,
        }
        values.update(overrides)
        return ChoreAssignment.objects.create(**values)

    def test_field_definitions(self):
        chore = ChoreAssignment._meta.get_field("chore")
        assigned_to = ChoreAssignment._meta.get_field("assigned_to")
        due_date = ChoreAssignment._meta.get_field("due_date")
        status = ChoreAssignment._meta.get_field("status")
        completed_at = ChoreAssignment._meta.get_field("completed_at")

        self.assertIs(chore.remote_field.model, Chore)
        self.assertIs(assigned_to.remote_field.model, Roommate)
        self.assertIsInstance(due_date, models.DateField)
        self.assertEqual(status.choices, ChoreAssignment.STATUS_CHOICES)
        self.assertEqual(status.default, ChoreAssignment.PENDING)
        self.assertIsInstance(completed_at, models.DateTimeField)

    def test_foreign_keys_use_cascade(self):
        self.assertIs(
            ChoreAssignment._meta.get_field("chore").remote_field.on_delete,
            models.CASCADE,
        )
        self.assertIs(
            ChoreAssignment._meta.get_field(
                "assigned_to"
            ).remote_field.on_delete,
            models.CASCADE,
        )

    def test_status_choices_are_exactly_the_three_statuses(self):
        self.assertEqual(
            [value for value, _ in ChoreAssignment.STATUS_CHOICES],
            ["PENDING", "COMPLETED", "PENALIZED"],
        )

    def test_status_accepts_each_choice(self):
        for value in ("PENDING", "COMPLETED", "PENALIZED"):
            with self.subTest(status=value):
                assignment = ChoreAssignment(
                    chore=self.chore,
                    assigned_to=self.roommate,
                    due_date=self.due_date,
                    status=value,
                )

                assignment.full_clean()

    def test_invalid_status_fails_full_clean_on_status(self):
        assignment = ChoreAssignment(
            chore=self.chore,
            assigned_to=self.roommate,
            due_date=self.due_date,
            status="CANCELLED",
        )

        with self.assertRaises(ValidationError) as context:
            assignment.full_clean()
        self.assertIn("status", context.exception.message_dict)

    def test_status_defaults_to_pending(self):
        assignment = self.create_assignment()

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, "PENDING")

    def test_completed_at_defaults_to_none(self):
        assignment = self.create_assignment()

        assignment.refresh_from_db()
        self.assertIsNone(assignment.completed_at)

    def test_completed_at_round_trips_an_aware_datetime(self):
        completed_at = timezone.make_aware(
            datetime.datetime(2026, 9, 14, 18, 30, 15)
        )

        assignment = self.create_assignment(completed_at=completed_at)
        assignment.refresh_from_db()

        self.assertEqual(assignment.completed_at, completed_at)

    def test_completed_at_is_nullable_and_blank(self):
        completed_at = ChoreAssignment._meta.get_field("completed_at")

        self.assertTrue(completed_at.null)
        self.assertTrue(completed_at.blank)

    def test_due_date_is_required(self):
        due_date = ChoreAssignment._meta.get_field("due_date")

        self.assertFalse(due_date.null)
        self.assertFalse(due_date.blank)

    def test_relationships_and_reverse_relations(self):
        assignment = self.create_assignment()

        self.assertEqual(assignment.chore, self.chore)
        self.assertEqual(assignment.assigned_to, self.roommate)
        self.assertIn(assignment, self.chore.choreassignment_set.all())
        self.assertIn(assignment, self.roommate.choreassignment_set.all())

    def test_deleting_chore_cascades_to_assignments(self):
        self.create_assignment()

        self.chore.delete()

        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_deleting_roommate_cascades_to_assignments(self):
        self.create_assignment()

        self.roommate.delete()

        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_roommate_can_hold_several_assignments(self):
        other_chore = Chore.objects.create(title="Dishes", recurrence_day=1)

        self.create_assignment()
        self.create_assignment(chore=other_chore)

        self.assertEqual(
            self.roommate.choreassignment_set.count(), 2
        )

    def test_same_chore_with_different_due_dates_persists(self):
        self.create_assignment()
        self.create_assignment(due_date=datetime.date(2026, 9, 21))

        self.assertEqual(
            ChoreAssignment.objects.filter(chore=self.chore).count(), 2
        )

    def test_status_has_no_uniqueness_constraint(self):
        self.create_assignment()
        self.create_assignment(due_date=datetime.date(2026, 9, 21))

        self.assertEqual(
            ChoreAssignment.objects.filter(status="PENDING").count(), 2
        )
