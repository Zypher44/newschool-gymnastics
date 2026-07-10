from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CoachProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coach_profile'
    )
    title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def save(self, *args, **kwargs):
        if self.user.role not in ['coach', 'head_coach']:
            raise ValidationError('User must be a coach or head coach.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Coach: {self.user.get_full_name() or self.user.username}"


class CoachAthleteAssignment(models.Model):
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_athletes'
    )
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_coaches'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.coach.role not in ['coach', 'head_coach']:
            raise ValidationError('Coach must have coach role.')
        if self.athlete.role != 'athlete':
            raise ValidationError('Athlete must have athlete role.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.coach.username} -> {self.athlete.username}"


class CoachNote(models.Model):
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coach_notes'
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes_written'
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.athlete.role != 'athlete':
            raise ValidationError('Note must be attached to an athlete.')
        if self.coach.role not in ['coach', 'head_coach']:
            raise ValidationError('Only coaches can write notes.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Note for {self.athlete.username} by {self.coach.username}"


class TeamEvent(models.Model):
    title = models.CharField(max_length=200)
    event_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_events_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', 'start_time']

    def __str__(self):
        return self.title