from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from chores.models import ChoreAssignment
from chores.models import Roommate
from chores.services import complete_assignment


def dashboard(request):
    """Render the leaderboard and the current week's chore board."""
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    roommates = Roommate.objects.order_by("-total_points", "id")
    assignments = (
        ChoreAssignment.objects.filter(
            due_date__gte=week_start,
            due_date__lte=week_end,
        )
        .select_related("chore", "assigned_to")
        .order_by("due_date", "id")
    )

    assignments_by_day = {}
    for assignment in assignments:
        assignments_by_day.setdefault(assignment.due_date, []).append(assignment)

    assignment_days = [
        {"date": day, "assignments": assignments_by_day[day]}
        for day in (week_start + timedelta(days=offset) for offset in range(7))
        if day in assignments_by_day
    ]

    context = {
        "roommates": roommates,
        "assignment_days": assignment_days,
        "week_start": week_start,
        "week_end": week_end,
    }
    return render(request, "chores/dashboard.html", context)


@require_POST
def complete_chore(request, id):
    """Complete a chore assignment and redirect back to the dashboard."""
    assignment = get_object_or_404(ChoreAssignment, pk=id)
    complete_assignment(assignment)
    return redirect("/")
