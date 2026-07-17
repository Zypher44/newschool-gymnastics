from django.contrib import admin

from .models import (
    AthleteTestingResult,
    TestingExercise,
    TestingExerciseResult,
    TestingScoringRule,
    TestingSession,
)


class TestingScoringRuleInline(admin.TabularInline):
    model = TestingScoringRule
    extra = 1


@admin.register(TestingExercise)
class TestingExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'unit',
        'higher_is_better',
        'active',
        'display_order',
    )

    list_filter = (
        'unit',
        'higher_is_better',
        'active',
    )

    search_fields = (
        'name',
        'description',
        'guidelines',
    )

    ordering = (
        'display_order',
        'name',
    )

    inlines = [
        TestingScoringRuleInline,
    ]


@admin.register(TestingSession)
class TestingSessionAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'testing_date',
        'created_by',
        'allow_athlete_entry',
        'published_to_athletes',
        'published_to_parents',
    )

    list_filter = (
        'testing_date',
        'allow_athlete_entry',
        'published_to_athletes',
        'published_to_parents',
    )

    search_fields = (
        'title',
        'notes',
    )

    filter_horizontal = (
        'exercises',
    )

    ordering = (
        '-testing_date',
    )


class TestingExerciseResultInline(admin.TabularInline):
    model = TestingExerciseResult
    extra = 0


@admin.register(AthleteTestingResult)
class AthleteTestingResultAdmin(admin.ModelAdmin):
    list_display = (
        'athlete',
        'session',
        'total_score',
        'rank',
        'status',
        'entered_by',
        'verified_by',
    )

    list_filter = (
        'status',
        'session',
    )

    search_fields = (
        'athlete__username',
        'athlete__first_name',
        'athlete__last_name',
        'session__title',
    )

    autocomplete_fields = (
        'athlete',
        'entered_by',
        'verified_by',
    )

    inlines = [
        TestingExerciseResultInline,
    ]


@admin.register(TestingExerciseResult)
class TestingExerciseResultAdmin(admin.ModelAdmin):
    list_display = (
        'athlete_result',
        'exercise',
        'raw_result',
        'numeric_result',
        'score',
        'not_completed',
    )

    list_filter = (
        'exercise',
        'not_completed',
    )

    search_fields = (
        'athlete_result__athlete__username',
        'exercise__name',
        'raw_result',
    )


@admin.register(TestingScoringRule)
class TestingScoringRuleAdmin(admin.ModelAdmin):
    list_display = (
        'exercise',
        'label',
        'comparison',
        'minimum_value',
        'maximum_value',
        'points',
        'active',
    )

    list_filter = (
        'exercise',
        'comparison',
        'active',
    )