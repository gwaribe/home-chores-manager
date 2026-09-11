from django.core.exceptions import ValidationError
from django.test import TestCase

from chores.models import Roommate


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
