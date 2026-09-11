import datetime
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import models
from django.template import Context
from django.template import Template
from django.template import loader
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chores.models import ChoreAssignment
from chores.models import Roommate
from chores.models import Chore
from chores.services import complete_assignment
from chores.services import generate_weekly_assignments
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


class AdminRegistrationTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.force_login(self.admin_user)

    def test_admin_index_lists_all_three_models(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roommates")
        self.assertContains(response, "Chores")
        self.assertContains(response, "Chore assignments")

    def test_roommate_admin_list_display(self):
        model_admin = admin.site._registry[Roommate]

        self.assertEqual(
            list(model_admin.list_display), ["name", "total_points"]
        )

    def test_chore_admin_list_display(self):
        model_admin = admin.site._registry[Chore]

        self.assertEqual(
            list(model_admin.list_display),
            ["title", "weight", "recurrence_day", "is_active"],
        )

    def test_chore_assignment_admin_list_display(self):
        model_admin = admin.site._registry[ChoreAssignment]

        self.assertEqual(
            list(model_admin.list_display),
            ["chore", "assigned_to", "due_date", "status"],
        )

    def test_changelist_pages_return_200(self):
        urls = [
            "/admin/chores/roommate/",
            "/admin/chores/chore/",
            "/admin/chores/choreassignment/",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_pages_return_200(self):
        urls = [
            "/admin/chores/roommate/add/",
            "/admin/chores/chore/add/",
            "/admin/chores/choreassignment/add/",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_post_creates_roommate(self):
        response = self.client.post(
            "/admin/chores/roommate/add/",
            {"name": "Alex", "total_points": "0"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Roommate.objects.filter(name="Alex").exists())

    def test_post_creates_chore(self):
        response = self.client.post(
            "/admin/chores/chore/add/",
            {
                "title": "Trash",
                "description": "",
                "weight": "1",
                "recurrence_day": "0",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Chore.objects.filter(title="Trash").exists())

    def test_post_creates_chore_assignment(self):
        roommate = Roommate.objects.create(name="Alex")
        chore = Chore.objects.create(title="Trash")

        response = self.client.post(
            "/admin/chores/choreassignment/add/",
            {
                "chore": chore.pk,
                "assigned_to": roommate.pk,
                "due_date": "2026-09-14",
                "status": "PENDING",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ChoreAssignment.objects.filter(
                chore=chore, assigned_to=roommate
            ).exists()
        )


class GenerateWeeklyAssignmentsTests(TestCase):
    def setUp(self):
        # 2026-09-14 is a Monday.
        self.week_start = datetime.date(2026, 9, 14)

    def test_target_week_start_is_a_monday(self):
        self.assertEqual(self.week_start.weekday(), 0)

    def test_active_chore_is_assigned_on_its_recurrence_day(self):
        roommate = Roommate.objects.create(name="Alex")
        chore = Chore.objects.create(
            title="Trash", weight=2, recurrence_day=0, is_active=True
        )

        generate_weekly_assignments(self.week_start)

        assignment = ChoreAssignment.objects.get()
        self.assertEqual(assignment.chore, chore)
        self.assertEqual(assignment.assigned_to, roommate)
        self.assertEqual(assignment.due_date, self.week_start)

    def test_due_dates_cover_monday_through_sunday(self):
        Roommate.objects.create(name="Alex")
        chores = [
            Chore.objects.create(
                title=f"Chore {day}", weight=1, recurrence_day=day
            )
            for day in range(7)
        ]

        generate_weekly_assignments(self.week_start)

        for chore in chores:
            with self.subTest(recurrence_day=chore.recurrence_day):
                assignment = ChoreAssignment.objects.get(chore=chore)
                self.assertEqual(
                    assignment.due_date,
                    self.week_start
                    + datetime.timedelta(days=chore.recurrence_day),
                )
        self.assertEqual(ChoreAssignment.objects.count(), 7)

    def test_heaviest_chores_are_processed_first(self):
        low = Roommate.objects.create(name="Alex")
        high = Roommate.objects.create(name="Blair")
        heavy = Chore.objects.create(title="Deep clean", weight=4, recurrence_day=6)
        light = Chore.objects.create(title="Trash", weight=1, recurrence_day=0)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(
            ChoreAssignment.objects.get(chore=heavy).assigned_to, low
        )
        self.assertEqual(
            ChoreAssignment.objects.get(chore=light).assigned_to, high
        )

    def test_assignment_goes_to_lowest_score_roommate(self):
        Roommate.objects.create(name="Alex", total_points=5)
        low = Roommate.objects.create(name="Blair", total_points=1)
        chore = Chore.objects.create(title="Trash", weight=2)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(
            ChoreAssignment.objects.get(chore=chore).assigned_to, low
        )

    def test_roommate_score_tie_is_broken_by_primary_key(self):
        first = Roommate.objects.create(name="Alex")
        Roommate.objects.create(name="Blair")
        chore = Chore.objects.create(title="Trash", weight=1)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(
            ChoreAssignment.objects.get(chore=chore).assigned_to, first
        )

    def test_equal_weight_chores_are_processed_by_id(self):
        first_roommate = Roommate.objects.create(name="Alex")
        second_roommate = Roommate.objects.create(name="Blair")
        first_chore = Chore.objects.create(title="Trash", weight=2)
        second_chore = Chore.objects.create(title="Dishes", weight=2)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(
            ChoreAssignment.objects.get(chore=first_chore).assigned_to,
            first_roommate,
        )
        self.assertEqual(
            ChoreAssignment.objects.get(chore=second_chore).assigned_to,
            second_roommate,
        )

    def test_existing_pairs_are_skipped(self):
        Roommate.objects.create(name="Alex")
        chore = Chore.objects.create(title="Trash", weight=2)

        generate_weekly_assignments(self.week_start)
        generate_weekly_assignments(self.week_start)

        self.assertEqual(
            ChoreAssignment.objects.filter(chore=chore).count(), 1
        )

    def test_inactive_chores_get_no_assignment(self):
        Roommate.objects.create(name="Alex")
        Chore.objects.create(title="Trash", is_active=False)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_zero_roommates_creates_nothing_and_does_not_raise(self):
        Chore.objects.create(title="Trash", weight=2)

        generate_weekly_assignments(self.week_start)

        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_generator_does_not_persist_point_balances(self):
        roommate = Roommate.objects.create(name="Alex", total_points=0)
        Chore.objects.create(title="Trash", weight=3)

        generate_weekly_assignments(self.week_start)

        roommate.refresh_from_db()
        self.assertEqual(roommate.total_points, 0)
        self.assertEqual(ChoreAssignment.objects.count(), 1)

    def test_created_assignments_are_pending_and_uncompleted(self):
        Roommate.objects.create(name="Alex")
        Chore.objects.create(title="Trash", weight=3)

        generate_weekly_assignments(self.week_start)

        assignment = ChoreAssignment.objects.get()
        self.assertEqual(assignment.status, ChoreAssignment.PENDING)
        self.assertIsNone(assignment.completed_at)


class CompleteAssignmentTests(TestCase):
    def setUp(self):
        self.roommate = Roommate.objects.create(name="Alex", total_points=0)
        self.chore = Chore.objects.create(title="Trash", weight=3)
        self.assignment = ChoreAssignment.objects.create(
            chore=self.chore,
            assigned_to=self.roommate,
            due_date=datetime.date(2026, 9, 14),
        )

    def test_pending_assignment_transitions_to_completed(self):
        result = complete_assignment(self.assignment)

        self.assertTrue(result)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ChoreAssignment.COMPLETED)

    def test_completed_at_is_stamped_with_an_aware_datetime(self):
        before = timezone.now()

        complete_assignment(self.assignment)

        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.completed_at)
        self.assertTrue(timezone.is_aware(self.assignment.completed_at))
        self.assertGreaterEqual(self.assignment.completed_at, before)
        self.assertLessEqual(self.assignment.completed_at, timezone.now())

    def test_weight_is_credited_to_the_roommate(self):
        complete_assignment(self.assignment)

        self.roommate.refresh_from_db()
        self.assertEqual(self.roommate.total_points, 3)

    def test_double_completion_credits_points_once(self):
        first = complete_assignment(self.assignment)
        second = complete_assignment(self.assignment)

        self.assertTrue(first)
        self.assertFalse(second)
        self.roommate.refresh_from_db()
        self.assertEqual(self.roommate.total_points, 3)
        self.assertEqual(
            ChoreAssignment.objects.filter(
                status=ChoreAssignment.COMPLETED
            ).count(),
            1,
        )

    def test_penalized_assignment_is_refused_and_unchanged(self):
        self.assignment.status = ChoreAssignment.PENALIZED
        self.assignment.save()

        result = complete_assignment(self.assignment)

        self.assertFalse(result)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ChoreAssignment.PENALIZED)
        self.assertIsNone(self.assignment.completed_at)
        self.roommate.refresh_from_db()
        self.assertEqual(self.roommate.total_points, 0)

    def test_completed_assignment_is_refused_and_unchanged(self):
        completed_at = timezone.make_aware(
            datetime.datetime(2026, 9, 14, 9, 0, 0)
        )
        self.assignment.status = ChoreAssignment.COMPLETED
        self.assignment.completed_at = completed_at
        self.assignment.save()

        result = complete_assignment(self.assignment)

        self.assertFalse(result)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.completed_at, completed_at)
        self.roommate.refresh_from_db()
        self.assertEqual(self.roommate.total_points, 0)

    def test_status_change_rolls_back_when_point_credit_fails(self):
        with mock.patch("chores.services.F", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                complete_assignment(self.assignment)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ChoreAssignment.PENDING)
        self.assertIsNone(self.assignment.completed_at)
        self.roommate.refresh_from_db()
        self.assertEqual(self.roommate.total_points, 0)


class RunPenaltyCheckCommandTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.roommate = Roommate.objects.create(name="Alex", total_points=10)
        self.chore = Chore.objects.create(title="Trash", weight=3)

    def create_assignment(self, due_date, status=ChoreAssignment.PENDING):
        return ChoreAssignment.objects.create(
            chore=self.chore,
            assigned_to=self.roommate,
            due_date=due_date,
            status=status,
        )

    def test_command_is_discoverable(self):
        from django.core.management import get_commands

        self.assertEqual(
            get_commands().get("run_penalty_check"),
            "chores",
        )

    def test_overdue_pending_assignment_is_penalized_and_deducted(self):
        assignment = self.create_assignment(
            self.today - datetime.timedelta(days=1)
        )

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENALIZED)
        self.assertIsNone(assignment.completed_at)
        self.assertEqual(self.roommate.total_points, 7)

    def test_assignment_due_today_is_untouched(self):
        assignment = self.create_assignment(self.today)

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENDING)
        self.assertEqual(self.roommate.total_points, 10)

    def test_future_assignment_is_untouched(self):
        assignment = self.create_assignment(
            self.today + datetime.timedelta(days=1)
        )

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENDING)
        self.assertEqual(self.roommate.total_points, 10)

    def test_completed_assignment_is_untouched(self):
        assignment = self.create_assignment(
            self.today - datetime.timedelta(days=1),
            status=ChoreAssignment.COMPLETED,
        )

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.COMPLETED)
        self.assertEqual(self.roommate.total_points, 10)

    def test_already_penalized_assignment_is_untouched(self):
        assignment = self.create_assignment(
            self.today - datetime.timedelta(days=1),
            status=ChoreAssignment.PENALIZED,
        )

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENALIZED)
        self.assertEqual(self.roommate.total_points, 10)

    def test_second_run_changes_nothing(self):
        assignment = self.create_assignment(
            self.today - datetime.timedelta(days=1)
        )

        call_command("run_penalty_check")
        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENALIZED)
        self.assertEqual(self.roommate.total_points, 7)

    def test_no_overdue_assignments_is_a_noop(self):
        assignment = self.create_assignment(self.today)

        call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENDING)
        self.assertEqual(self.roommate.total_points, 10)

    def test_penalties_use_each_assignments_own_weight(self):
        heavy_chore = Chore.objects.create(title="Deep clean", weight=5)
        other_roommate = Roommate.objects.create(name="Blair", total_points=10)
        ChoreAssignment.objects.create(
            chore=heavy_chore,
            assigned_to=other_roommate,
            due_date=self.today - datetime.timedelta(days=2),
        )

        call_command("run_penalty_check")

        other_roommate.refresh_from_db()
        self.assertEqual(other_roommate.total_points, 5)

    def test_status_change_rolls_back_when_deduction_fails(self):
        assignment = self.create_assignment(
            self.today - datetime.timedelta(days=1)
        )

        with mock.patch(
            "chores.management.commands.run_penalty_check.F",
            side_effect=RuntimeError,
        ):
            with self.assertRaises(RuntimeError):
                call_command("run_penalty_check")

        assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(assignment.status, ChoreAssignment.PENDING)
        self.assertEqual(self.roommate.total_points, 10)


class BaseTemplateTests(TestCase):
    def render_child(self):
        template = Template(
            "{% extends \"chores/base.html\" %}"
            "{% block content %}<p>Child body</p>{% endblock %}"
        )
        return template.render(Context({}))

    def test_base_template_is_discoverable_by_the_loader(self):
        template = loader.get_template("chores/base.html")

        self.assertIsNotNone(template)

    def test_child_template_extends_and_renders_its_content(self):
        html = self.render_child()

        self.assertIn("Child body", html)

    def test_rendered_html_includes_the_pico_cdn_link(self):
        html = self.render_child()

        self.assertIn(
            'href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"',
            html,
        )

    def test_rendered_html_includes_nav_with_admin_link(self):
        html = self.render_child()

        self.assertIn("<nav>", html)
        self.assertIn('href="/admin/"', html)

    def test_rendered_html_wraps_content_in_the_container(self):
        html = self.render_child()

        self.assertIn('<main class="container">', html)
        self.assertIn("Child body", html.split('<main class="container">')[1])


def monday_of(day):
    return day - datetime.timedelta(days=day.weekday())


class DashboardViewTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.week_start = monday_of(self.today)

    def create_assignment(
        self, title="Trash", weight=3, due_date=None, roommate_name="Alex"
    ):
        roommate = Roommate.objects.create(name=roommate_name)
        chore = Chore.objects.create(title=title, weight=weight, recurrence_day=0)
        if due_date is None:
            due_date = self.today
        return ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=roommate,
            due_date=due_date,
        )

    def test_root_returns_200(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

    def test_empty_database_returns_200_and_empty_state(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No roommates yet")
        self.assertContains(response, "No chores assigned for this week")

    def test_no_assignments_but_roommates_returns_empty_state(self):
        Roommate.objects.create(name="Alex", total_points=5)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex")
        self.assertContains(response, "No chores assigned for this week")

    def test_leaderboard_orders_by_points_desc_then_id(self):
        low_first = Roommate.objects.create(name="Alex", total_points=5)
        high = Roommate.objects.create(name="Blair", total_points=10)
        low_second = Roommate.objects.create(name="Casey", total_points=5)

        response = self.client.get("/")

        self.assertEqual(
            list(response.context["roommates"]),
            [high, low_first, low_second],
        )

    def test_leaderboard_renders_names_and_points(self):
        Roommate.objects.create(name="Blair", total_points=12)

        response = self.client.get("/")

        self.assertContains(response, "Blair")
        self.assertContains(response, "12")

    def test_assignment_renders_key_fields(self):
        self.create_assignment(title="Bathroom Deep Clean", weight=4)

        response = self.client.get("/")

        self.assertContains(response, "Bathroom Deep Clean")
        self.assertContains(response, "<mark>4</mark>", html=True)
        self.assertContains(response, "Alex")
        self.assertContains(response, 'data-status="PENDING"')
        self.assertContains(response, "Pending")

    def test_pending_assignment_renders_complete_form(self):
        assignment = self.create_assignment()

        response = self.client.get("/")

        self.assertContains(response, 'method="post"')
        self.assertContains(
            response, f'action="/assignments/{assignment.id}/complete/"'
        )
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_completed_assignment_has_no_complete_form(self):
        assignment = self.create_assignment()
        assignment.status = ChoreAssignment.COMPLETED
        assignment.save()

        response = self.client.get("/")

        self.assertContains(response, 'data-status="COMPLETED"')
        self.assertNotContains(
            response,
            f'<form method="post" action="/assignments/{assignment.id}/complete/">',
        )

    def test_assignments_from_other_weeks_are_not_shown(self):
        self.create_assignment(
            title="Last Week Chore", due_date=self.week_start - datetime.timedelta(days=1)
        )
        self.create_assignment(
            title="Next Week Chore", due_date=self.week_start + datetime.timedelta(days=7)
        )

        response = self.client.get("/")

        self.assertNotContains(response, "Last Week Chore")
        self.assertNotContains(response, "Next Week Chore")

    def test_assignments_are_grouped_by_day(self):
        monday = self.create_assignment(
            title="Monday Chore", due_date=self.week_start
        )
        sunday = self.create_assignment(
            title="Sunday Chore", due_date=self.week_start + datetime.timedelta(days=6)
        )

        response = self.client.get("/")

        days = response.context["assignment_days"]
        self.assertEqual([entry["date"] for entry in days], [self.week_start, self.week_start + datetime.timedelta(days=6)])
        self.assertEqual(days[0]["assignments"], [monday])
        self.assertEqual(days[1]["assignments"], [sunday])


class CompleteChoreEndpointTests(TestCase):
    def setUp(self):
        self.roommate = Roommate.objects.create(name="Alex", total_points=1)
        self.chore = Chore.objects.create(title="Trash", weight=4)
        self.assignment = ChoreAssignment.objects.create(
            chore=self.chore,
            assigned_to=self.roommate,
            due_date=timezone.localdate(),
        )

    def complete_url(self, assignment=None):
        assignment = assignment or self.assignment
        return f"/assignments/{assignment.id}/complete/"

    def test_post_completes_pending_assignment_and_credits_once(self):
        response = self.client.post(self.complete_url())

        self.assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.status, ChoreAssignment.COMPLETED)
        self.assertIsNotNone(self.assignment.completed_at)
        self.assertEqual(self.roommate.total_points, 5)

    def test_post_redirects_to_root(self):
        response = self.client.post(self.complete_url())

        self.assertRedirects(response, "/")

    def test_get_returns_405_and_changes_nothing(self):
        response = self.client.get(self.complete_url())

        self.assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.assignment.status, ChoreAssignment.PENDING)
        self.assertEqual(self.roommate.total_points, 1)

    def test_repeated_post_does_not_double_complete(self):
        self.client.post(self.complete_url())
        response = self.client.post(self.complete_url())

        self.assignment.refresh_from_db()
        self.roommate.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.status, ChoreAssignment.COMPLETED)
        self.assertEqual(self.roommate.total_points, 5)

    def test_unknown_id_returns_404(self):
        response = self.client.post("/assignments/999999/complete/")

        self.assertEqual(response.status_code, 404)

    def test_non_integer_id_does_not_match_the_route(self):
        response = self.client.post("/assignments/abc/complete/")

        self.assertEqual(response.status_code, 404)

    def test_post_without_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(self.complete_url())

        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.assignment.status, ChoreAssignment.PENDING)

    def test_post_with_csrf_token_succeeds_when_checks_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/")
        token = client.cookies["csrftoken"].value

        response = client.post(self.complete_url(), HTTP_X_CSRFTOKEN=token)

        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.status, ChoreAssignment.COMPLETED)

    def test_normal_test_client_post_succeeds(self):
        response = self.client.post(self.complete_url())

        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.status, ChoreAssignment.COMPLETED)


class GenerateCycleEndpointTests(TestCase):
    def current_week_start(self):
        today = timezone.localdate()
        return today - datetime.timedelta(days=today.weekday())

    def test_get_creates_this_weeks_assignments_and_redirects(self):
        roommate = Roommate.objects.create(name="Alex")
        chore = Chore.objects.create(
            title="Trash", weight=2, recurrence_day=2, is_active=True
        )

        response = self.client.get("/generate-cycle/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        assignment = ChoreAssignment.objects.get()
        self.assertEqual(assignment.chore, chore)
        self.assertEqual(assignment.assigned_to, roommate)
        self.assertEqual(
            assignment.due_date,
            self.current_week_start() + datetime.timedelta(days=2),
        )

    def test_url_route_is_named(self):
        self.assertEqual(reverse("generate_cycle"), "/generate-cycle/")

    def test_second_call_leaves_assignment_count_unchanged(self):
        Roommate.objects.create(name="Alex")
        Chore.objects.create(title="Trash", weight=2)
        Chore.objects.create(title="Dishes", weight=1, recurrence_day=3)

        self.client.get("/generate-cycle/")
        first_count = ChoreAssignment.objects.count()
        self.client.get("/generate-cycle/")

        self.assertEqual(first_count, 2)
        self.assertEqual(ChoreAssignment.objects.count(), 2)

    def test_redirects_when_there_are_no_roommates(self):
        Chore.objects.create(title="Trash", weight=2, is_active=True)

        response = self.client.get("/generate-cycle/")

        self.assertRedirects(response, "/")
        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_redirects_when_there_are_no_active_chores(self):
        Roommate.objects.create(name="Alex")
        Chore.objects.create(title="Trash", weight=2, is_active=False)

        response = self.client.get("/generate-cycle/")

        self.assertRedirects(response, "/")
        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_dashboard_renders_the_generate_cycle_trigger(self):
        response = self.client.get("/")

        self.assertContains(response, 'href="/generate-cycle/"')


class SeedDataCommandTests(TestCase):
    def test_command_is_discoverable(self):
        from django.core.management import get_commands

        self.assertEqual(get_commands().get("seed_data"), "chores")

    def test_fresh_run_creates_three_or_four_roommates(self):
        call_command("seed_data")

        self.assertIn(Roommate.objects.count(), (3, 4))
        for roommate in Roommate.objects.all():
            self.assertTrue(roommate.name)

    def test_fresh_run_creates_chores_with_varied_weights_and_days(self):
        call_command("seed_data")

        chores = Chore.objects.all()
        self.assertGreaterEqual(chores.count(), 3)
        weights = set(chores.values_list("weight", flat=True))
        days = set(chores.values_list("recurrence_day", flat=True))
        self.assertTrue(weights.issubset({1, 2, 3, 4}))
        self.assertEqual(weights, {1, 2, 3, 4})
        self.assertGreater(len(days), 1)

    def test_every_seeded_chore_is_active_and_has_a_title(self):
        call_command("seed_data")

        for chore in Chore.objects.all():
            with self.subTest(title=chore.title):
                self.assertTrue(chore.is_active)
                self.assertTrue(chore.title)

    def test_running_twice_produces_no_duplicates(self):
        call_command("seed_data")
        roommate_count = Roommate.objects.count()
        chore_count = Chore.objects.count()

        call_command("seed_data")

        self.assertEqual(Roommate.objects.count(), roommate_count)
        self.assertEqual(Chore.objects.count(), chore_count)

    def test_creates_no_assignments(self):
        call_command("seed_data")

        self.assertEqual(ChoreAssignment.objects.count(), 0)

    def test_prints_a_summary(self):
        import io

        output = io.StringIO()

        call_command("seed_data", stdout=output)

        self.assertIn("Seed complete", output.getvalue())

    def test_partial_data_does_not_duplicate(self):
        Roommate.objects.create(name="Alex")
        Chore.objects.create(title="Empty Kitchen Trash", weight=1)

        call_command("seed_data")

        self.assertEqual(Roommate.objects.filter(name="Alex").count(), 1)
        self.assertEqual(
            Chore.objects.filter(title="Empty Kitchen Trash").count(), 1
        )
        self.assertIn(Roommate.objects.count(), (3, 4))
