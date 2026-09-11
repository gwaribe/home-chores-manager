from django.contrib import admin

from chores.models import Chore
from chores.models import ChoreAssignment
from chores.models import Roommate


@admin.register(Roommate)
class RoommateAdmin(admin.ModelAdmin):
    list_display = ("name", "total_points")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "weight", "recurrence_day", "is_active")


@admin.register(ChoreAssignment)
class ChoreAssignmentAdmin(admin.ModelAdmin):
    list_display = ("chore", "assigned_to", "due_date", "status")
