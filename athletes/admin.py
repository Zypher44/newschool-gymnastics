from django.contrib import admin

from .models import (
    AthleteProfile,
    AttendanceRecord,
    Skill,
    AthleteSkill,
    AthleteVideo,
)


@admin.register(AthleteProfile)
class AthleteProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'level',
        'team_name',
        'training_group',
    )

    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'level',
        'team_name',
    )

    list_filter = (
        'level',
        'team_name',
        'training_group',
    )

    fieldsets = (
        (
            'Athlete Information',
            {
                'fields': (
                    'user',
                    'date_of_birth',
                    'level',
                    'team_name',
                    'training_group',
                )
            },
        ),
        (
            'Emergency Contact',
            {
                'fields': (
                    'emergency_contact_name',
                    'emergency_contact_relationship',
                    'emergency_contact_phone',
                )
            },
        ),
        (
            'Medical Information',
            {
                'fields': (
                    'medical_notes',
                )
            },
        ),
        (
            'Additional Notes',
            {
                'fields': (
                    'notes',
                )
            },
        ),
    )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):

    list_display = (
        'attendance_date',
        'athlete',
        'status',
        'coach',
    )

    list_filter = (
        'attendance_date',
        'status',
        'coach',
    )

    search_fields = (
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'notes',
    )

    date_hierarchy = 'attendance_date'

    ordering = (
        '-attendance_date',
        'athlete__username',
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'event',
    )

    list_filter = (
        'event',
    )

    search_fields = (
        'name',
        'description',
    )

    ordering = (
        'event',
        'name',
    )


@admin.register(AthleteSkill)
class AthleteSkillAdmin(admin.ModelAdmin):

    list_display = (
        'athlete',
        'skill',
        'status',
        'coach',
        'started_date',
        'achieved_date',
        'updated_at',
    )

    list_filter = (
        'status',
        'skill__event',
        'coach',
    )

    search_fields = (
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'skill__name',
        'notes',
    )

    ordering = (
        'athlete__username',
        'skill__event',
        'skill__name',
    )


@admin.register(AthleteVideo)
class AthleteVideoAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'athlete',
        'skill',
        'uploaded_by',
        'uploaded_at',
    )

    list_filter = (
        'skill__event',
        'skill',
        'uploaded_by',
        'uploaded_at',
    )

    search_fields = (
        'title',
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'skill__name',
        'notes',
    )

    ordering = (
        '-uploaded_at',
    )