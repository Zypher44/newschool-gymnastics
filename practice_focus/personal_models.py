from django.conf import settings
from django.db import models


class AthletePracticePlan(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='individual_practice_plans')
    practice_date = models.DateField()
    title = models.CharField(max_length=150, default='Daily practice')
    level = models.CharField(max_length=100, blank=True)
    focus = models.CharField(max_length=250, blank=True)
    notes = models.TextField(max_length=3000, blank=True)
    content = models.JSONField(default=dict)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-practice_date', 'athlete_id']
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'practice_date'], name='unique_individual_daily_plan')]


class PracticePlanTemplate(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    key = models.CharField(max_length=150)
    level = models.CharField(max_length=100, blank=True)
    focus = models.CharField(max_length=250, blank=True)
    notes = models.TextField(max_length=3000, blank=True)
    content = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.UniqueConstraint(fields=['gym', 'key'], name='unique_individual_plan_template')]
