from django.contrib import admin

from .models import (
    CoachProfile,
    CoachAthleteAssignment,
    CoachNote,
    TeamEvent,
)


@admin.register(CoachProfile)
class CoachProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'phone')


@admin.register(CoachAthleteAssignment)
class CoachAthleteAssignmentAdmin(admin.ModelAdmin):
    list_display = ('coach', 'athlete', 'created_at')
    list_filter = ('coach',)
    search_fields = ('coach__username', 'athlete__username')


@admin.register(CoachNote)
class CoachNoteAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'coach', 'created_at')
    list_filter = ('coach', 'created_at')
    search_fields = (
        'athlete__username',
        'coach__username',
        'note',
    )


@admin.register(TeamEvent)
class TeamEventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'event_date',
        'start_time',
        'location',
    )
    list_filter = ('event_date',)
    search_fields = (
        'title',
        'location',
        'description',
    )