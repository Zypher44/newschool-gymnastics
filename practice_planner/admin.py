from django.contrib import admin

from .models import (
    PracticeAthleteAssignment,
    PracticePlan,
    PracticeRotation,
    PracticeStation,
    TrainingGroup,
)


class PracticeStationInline(admin.TabularInline):
    model = PracticeStation
    extra = 0

    fields = [
        'order',
        'title',
        'station_type',
        'duration_minutes',
        'sets',
        'repetitions',
        'target_attempts',
        'is_optional',
    ]

    ordering = [
        'order',
    ]


@admin.register(PracticeRotation)
class PracticeRotationAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'practice_plan',
        'event',
        'order',
        'duration_minutes',
        'assigned_coach',
        'is_testing_rotation',
    ]

    list_filter = [
        'event',
        'is_testing_rotation',
        'practice_plan__practice_date',
    ]

    search_fields = [
        'title',
        'practice_plan__title',
        'practice_plan__training_group__name',
    ]

    ordering = [
        '-practice_plan__practice_date',
        'order',
    ]

    inlines = [
        PracticeStationInline,
    ]


class PracticeRotationInline(admin.TabularInline):
    model = PracticeRotation
    extra = 0

    fields = [
        'order',
        'title',
        'event',
        'start_time',
        'duration_minutes',
        'assigned_coach',
        'is_testing_rotation',
    ]

    ordering = [
        'order',
    ]


class PracticeAthleteAssignmentInline(admin.TabularInline):
    model = PracticeAthleteAssignment
    extra = 0

    fields = [
        'athlete',
        'workload',
        'is_expected',
        'individual_focus',
    ]


@admin.register(PracticePlan)
class PracticePlanAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'practice_date',
        'training_group',
        'lead_coach',
        'status',
        'planned_intensity',
        'start_time',
        'end_time',
    ]

    list_filter = [
        'status',
        'planned_intensity',
        'practice_date',
        'training_group',
    ]

    search_fields = [
        'title',
        'training_group__name',
        'lead_coach__username',
        'lead_coach__first_name',
        'lead_coach__last_name',
        'primary_focus',
    ]

    date_hierarchy = 'practice_date'

    ordering = [
        '-practice_date',
        '-start_time',
    ]

    filter_horizontal = [
        'assistant_coaches',
    ]

    inlines = [
        PracticeRotationInline,
        PracticeAthleteAssignmentInline,
    ]


@admin.register(TrainingGroup)
class TrainingGroupAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'is_active',
        'athlete_count',
        'coach_count',
        'updated_at',
    ]

    list_filter = [
        'is_active',
    ]

    search_fields = [
        'name',
        'description',
    ]

    filter_horizontal = [
        'coaches',
        'athletes',
    ]

    def athlete_count(self, obj):
        return obj.athletes.count()

    athlete_count.short_description = 'Athletes'

    def coach_count(self, obj):
        return obj.coaches.count()

    coach_count.short_description = 'Coaches'


@admin.register(PracticeStation)
class PracticeStationAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'rotation',
        'station_type',
        'order',
        'duration_minutes',
        'is_optional',
    ]

    list_filter = [
        'station_type',
        'is_optional',
        'rotation__event',
    ]

    search_fields = [
        'title',
        'rotation__title',
        'rotation__practice_plan__title',
        'instructions',
        'coaching_cues',
    ]

    ordering = [
        '-rotation__practice_plan__practice_date',
        'rotation__order',
        'order',
    ]


@admin.register(PracticeAthleteAssignment)
class PracticeAthleteAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'athlete',
        'practice_plan',
        'workload',
        'is_expected',
    ]

    list_filter = [
        'workload',
        'is_expected',
        'practice_plan__practice_date',
    ]

    search_fields = [
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'practice_plan__title',
        'individual_focus',
        'restrictions',
    ]


from django.contrib import admin

# Register your models here.
