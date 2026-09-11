from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from chores.models import Chore
from chores.models import ChoreAssignment
from chores.models import Roommate


def generate_weekly_assignments(target_week_start):
    """Create one assignment per active chore for the target week.

    ``target_week_start`` is the Monday ``date`` of the target week. Each
    active chore is assigned to the roommate with the lowest running score,
    where scores start from ``Roommate.total_points`` and are kept in a
    batch-local dict so intra-week balancing does not persist to the
    database. Chores are processed heaviest first (ties broken by ``id``) and
    any ``(chore, due_date)`` pair that already exists is skipped, so calling
    this twice for the same week creates no duplicates.

    The return value is unspecified; callers ignore it.
    """
    active_chores = Chore.objects.filter(is_active=True).order_by("-weight", "id")
    roommates = list(Roommate.objects.order_by("total_points", "id"))
    balances = {roommate.pk: roommate.total_points for roommate in roommates}

    if not roommates:
        return

    for chore in active_chores:
        due_date = target_week_start + timedelta(days=chore.recurrence_day)

        if ChoreAssignment.objects.filter(chore=chore, due_date=due_date).exists():
            continue

        candidate = min(
            roommates, key=lambda roommate: (balances[roommate.pk], roommate.pk)
        )
        ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=candidate,
            due_date=due_date,
            status=ChoreAssignment.PENDING,
            completed_at=None,
        )
        balances[candidate.pk] += chore.weight


def complete_assignment(assignment):
    """Complete a PENDING assignment, crediting its points exactly once.

    Returns ``True`` when the assignment transitions from ``PENDING`` to
    ``COMPLETED``; returns ``False`` when it is refused because the
    assignment is already ``COMPLETED`` or ``PENALIZED``. The status change
    and the point credit happen in a single ``transaction.atomic()`` block,
    and the point credit uses a conditional update so a repeated call can
    never credit ``chore.weight`` twice.
    """
    with transaction.atomic():
        claimed = ChoreAssignment.objects.filter(
            pk=assignment.pk,
            status=ChoreAssignment.PENDING,
        ).update(
            status=ChoreAssignment.COMPLETED,
            completed_at=timezone.now(),
        )

        if claimed == 0:
            return False

        Roommate.objects.filter(pk=assignment.assigned_to_id).update(
            total_points=F("total_points") + assignment.chore.weight
        )

    assignment.refresh_from_db()
    return True
