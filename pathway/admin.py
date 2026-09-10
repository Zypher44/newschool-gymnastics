from django.contrib import admin

from .models import (
    AthletePathway,
    AthletePathwayRequirement,
    PathwayEvent,
    PathwayLevel,
    PathwayRequirement,
)

from .models import (
    AthletePathway,
    AthletePathwayRequirement,
    AthleteRoutine,
    AthleteRoutineElement,
    AthleteRoutineRequirement,
    PathwayEvent,
    PathwayLevel,
    PathwayRequirement,
)

@admin.register(AthleteRoutine)
class AthleteRoutineAdmin(admin.ModelAdmin):

    list_display = [
        'athlete',
        'event',
        'pathway_level',
        'name',
        'is_current',
        'created_by',
        'updated_at',
    ]

    list_filter = [
        'event',
        'pathway_level',
        'is_current',
    ]

    search_fields = [
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'name',
    ]


@admin.register(AthleteRoutineElement)
class AthleteRoutineElementAdmin(
    admin.ModelAdmin
):

    list_display = [
        'routine',
        'order',
        'skill_name',
        'difficulty',
        'difficulty_value',
        'element_type',
        'is_dismount',
    ]

    list_filter = [
        'difficulty',
        'element_type',
        'is_dismount',
    ]

    search_fields = [
        'skill_name',
        'routine__athlete__username',
        'routine__name',
    ]


@admin.register(AthleteRoutineRequirement)
class AthleteRoutineRequirementAdmin(
    admin.ModelAdmin
):

    list_display = [
        'routine',
        'requirement',
        'is_met',
    ]

    list_filter = [
        'is_met',
        'requirement__level',
        'requirement__event',
    ]



@admin.register(PathwayLevel)
class PathwayLevelAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'code',
        'order',
        'minimum_age',
        'maximum_age',
        'is_active',
    ]

    ordering = [
        'order',
    ]


@admin.register(PathwayEvent)
class PathwayEventAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'code',
        'order',
    ]

    ordering = [
        'order',
    ]


@admin.register(PathwayRequirement)
class PathwayRequirementAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'level',
        'event',
        'requirement_type',
        'requirement_number',
        'value',
        'bonus_value',
        'is_required',
    ]

    list_filter = [
        'level',
        'event',
        'requirement_type',
        'is_required',
        'is_active',
    ]

    search_fields = [
        'title',
        'description',
        'notes',
    ]


@admin.register(AthletePathway)
class AthletePathwayAdmin(admin.ModelAdmin):
    list_display = [
        'athlete',
        'current_level',
        'target_level',
        'status',
        'managed_by',
        'updated_at',
    ]

    list_filter = [
        'current_level',
        'target_level',
        'status',
    ]


@admin.register(AthletePathwayRequirement)
class AthletePathwayRequirementAdmin(
    admin.ModelAdmin
):
    list_display = [
        'athlete_pathway',
        'requirement',
        'status',
        'target_date',
        'updated_by',
        'updated_at',
    ]

    list_filter = [
        'status',
        'requirement__level',
        'requirement__event',
    ]

    search_fields = [
        'athlete_pathway__athlete__username',
        'requirement__title',
        'coach_note',
    ]


from django.contrib import admin

# Register your models here.
