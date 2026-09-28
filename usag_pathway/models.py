from django.conf import settings
from django.db import models

from gyms.models import Gym


class RequirementProgress(models.Model):
    """Private, gym-specific coach assessment, separate from HP progress."""

    STATUS_CHOICES = (
        ('not_started', 'Not started'),
        ('developing', 'Developing'),
        ('achieved', 'Achieved'),
        ('ready', 'Coach reviewed'),
    )

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='usag_requirement_progress',
    )
    level = models.PositiveSmallIntegerField()
    event = models.CharField(max_length=10)
    requirement_code = models.CharField(max_length=30)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('gym', 'athlete', 'level', 'requirement_code'),
                name='unique_gym_usag_requirement_progress',
            ),
        ]


class XcelRequirementProgress(models.Model):
    """Gym-specific assessments for Xcel; independent from HP and USAG levels."""

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='xcel_requirement_progress',
    )
    division = models.CharField(max_length=20)
    event = models.CharField(max_length=10)
    requirement_code = models.CharField(max_length=30)
    status = models.CharField(
        max_length=15, choices=RequirementProgress.STATUS_CHOICES,
        default='not_started',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('gym', 'athlete', 'division', 'requirement_code'),
                name='unique_gym_xcel_requirement_progress',
            ),
        ]
