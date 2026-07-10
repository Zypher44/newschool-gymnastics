from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import DailySurvey


@admin.register(DailySurvey)
class DailySurveyAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'survey_date', 'energy', 'soreness', 'stress', 'ate_well', 'hydrated')
    list_filter = ('survey_date', 'ate_well', 'hydrated')
    search_fields = ('athlete__username', 'athlete__first_name', 'athlete__last_name', 'notes', 'soreness_area')