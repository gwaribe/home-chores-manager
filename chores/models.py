from django.db import models


class Roommate(models.Model):
    name = models.CharField(max_length=60)
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Chore(models.Model):
    DAYS_OF_WEEK = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    weight = models.PositiveIntegerField(default=1)
    recurrence_day = models.IntegerField(choices=DAYS_OF_WEEK)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
