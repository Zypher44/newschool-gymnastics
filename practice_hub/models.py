from django.conf import settings
from django.db import models
from practice_focus.models import EVENTS


class PracticeSession(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    group = models.ForeignKey('gyms.TrainingGroup', on_delete=models.PROTECT)
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    practice_date = models.DateField()
    event = models.CharField(max_length=20, choices=EVENTS, default='floor')
    rotation_minutes = models.PositiveSmallIntegerField(default=15)
    rotation_started_at = models.DateTimeField()
    rotation_deadline = models.DateTimeField(null=True, blank=True)
    rotation_paused_seconds = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-practice_date', '-started_at']
        constraints = [models.UniqueConstraint(
            fields=['gym', 'coach', 'group', 'practice_date'], name='unique_coach_group_practice_day')]


class AthletePracticeTimer(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='athlete_timers')
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=20, choices=EVENTS, default='floor')
    minutes = models.PositiveSmallIntegerField(default=15)
    remaining_seconds = models.PositiveIntegerField(default=900)
    deadline = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['session', 'athlete'], name='unique_child_practice_timer')]


class OnboardingProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    role = models.CharField(max_length=20)
    completed_steps = models.JSONField(default=list)
    current_step = models.PositiveSmallIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['user', 'gym', 'role'], name='unique_person_gym_role_onboarding')]
