from django.conf import settings
from django.db import models


class CoachReportPreference(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    show_group_averages = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['gym', 'coach'], name='unique_coach_report_preference')]
