from django.contrib import admin

from .models import (
    DailyRoutineAttempt,
    DailyRoutineSession,
)


class DailyRoutineAttemptInline(
    admin.TabularInline
):

    model = DailyRoutineAttempt

    extra = 0

    fields = [
        'athlete',
        'event',
        'attempt_number',
        'result',
        'notes',
        'recorded_by',
    ]


@admin.register(DailyRoutineSession)
class DailyRoutineSessionAdmin(
    admin.ModelAdmin
):

    list_display = [
        'practice_date',
        'created_by',
        'created_at',
        'updated_at',
    ]

    search_fields = [
        'notes',
    ]

    inlines = [
        DailyRoutineAttemptInline,
    ]


@admin.register(DailyRoutineAttempt)
class DailyRoutineAttemptAdmin(
    admin.ModelAdmin
):

    list_display = [
        'athlete',
        'session',
        'event',
        'attempt_number',
        'result',
        'recorded_by',
    ]

    list_filter = [
        'event',
        'result',
        'session__practice_date',
    ]

    search_fields = [
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
    ]