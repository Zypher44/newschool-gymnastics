from django.conf import settings
from django.db import models


class PassportBadgeDefinition(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    code = models.CharField(max_length=30)
    variant = models.CharField(max_length=20, default='earned')
    title = models.CharField(max_length=80)
    icon = models.CharField(max_length=12, default='🏅')
    description = models.CharField(max_length=400)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title', 'pk']
        constraints = [models.UniqueConstraint(fields=['gym', 'code', 'variant'], name='unique_gym_passport_badge')]
