from django.conf import settings
from django.db import models


class PassportStamp(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    badge_code = models.CharField(max_length=30)
    variant = models.CharField(max_length=20)
    award_date = models.DateField()
    shared_note = models.CharField(max_length=500, blank=True)
    badge_snapshot = models.JSONField(default=dict, blank=True)
    awarded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    revoked_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'badge_code', 'variant'], name='unique_athlete_passport_stamp')]
        ordering = ['-award_date', '-pk']


class PassportAction(models.Model):
    stamp = models.ForeignKey(PassportStamp, on_delete=models.CASCADE, related_name='actions')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    action = models.CharField(max_length=10, choices=[('award', 'Award'), ('withdraw', 'Withdraw')])
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
