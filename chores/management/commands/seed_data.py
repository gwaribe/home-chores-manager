from django.core.management.base import BaseCommand

from chores.models import Chore
from chores.models import Roommate


ROOMMATE_NAMES = ["Alex", "Blair", "Casey", "Devon"]

CHORES = [
    {"title": "Empty Kitchen Trash", "weight": 1, "recurrence_day": 0},
    {"title": "Wipe Down Kitchen Counters", "weight": 2, "recurrence_day": 1},
    {"title": "Vacuum Living Room", "weight": 3, "recurrence_day": 2},
    {"title": "Clean Bathroom", "weight": 4, "recurrence_day": 3},
    {"title": "Water the Plants", "weight": 1, "recurrence_day": 4},
    {"title": "Mop the Floors", "weight": 3, "recurrence_day": 5},
    {"title": "Take Out Recycling", "weight": 2, "recurrence_day": 6},
]


class Command(BaseCommand):
    help = (
        "Seed demo roommates and chores. Safe to re-run: records are looked "
        "up by name/title, so existing data is skipped rather than duplicated."
    )

    def handle(self, *args, **options):
        roommates_created = 0
        roommates_skipped = 0
        for name in ROOMMATE_NAMES:
            _, created = Roommate.objects.get_or_create(name=name)
            if created:
                roommates_created += 1
            else:
                roommates_skipped += 1

        chores_created = 0
        chores_skipped = 0
        for spec in CHORES:
            _, created = Chore.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "weight": spec["weight"],
                    "recurrence_day": spec["recurrence_day"],
                    "is_active": True,
                },
            )
            if created:
                chores_created += 1
            else:
                chores_skipped += 1

        self.stdout.write(
            "Seed complete: "
            f"{roommates_created} roommate(s) created, "
            f"{roommates_skipped} skipped; "
            f"{chores_created} chore(s) created, "
            f"{chores_skipped} skipped."
        )
