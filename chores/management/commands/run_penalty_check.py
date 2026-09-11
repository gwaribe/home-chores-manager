from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from chores.models import ChoreAssignment
from chores.models import Roommate


class Command(BaseCommand):
    help = (
        "Mark overdue PENDING assignments as PENALIZED and deduct each "
        "chore's weight from the assignee's total_points."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()
        overdue = list(
            ChoreAssignment.objects.filter(
                status=ChoreAssignment.PENDING,
                due_date__lt=today,
            )
            .select_related("chore", "assigned_to")
            .order_by("pk")
        )

        for assignment in overdue:
            with transaction.atomic():
                assignment.status = ChoreAssignment.PENALIZED
                assignment.save(update_fields=["status"])
                Roommate.objects.filter(pk=assignment.assigned_to_id).update(
                    total_points=F("total_points") - assignment.chore.weight
                )

        self.stdout.write(
            f"Penalized {len(overdue)} overdue assignment(s)."
        )
