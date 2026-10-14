from django.conf import settings
from django.db import models


class TrackerMutation(models.Model):
    token = models.UUIDField(unique=True)
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    payload = models.JSONField(default=dict)
    response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class TrackedResult(models.Model):
    token = models.UUIDField(unique=True)
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    practice_date = models.DateField()
    kind = models.CharField(max_length=10, choices=[('skill', 'Skill'), ('routine', 'Routine')])
    details = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='pending', choices=[('pending', 'Needs review'), ('approved', 'Approved'), ('rejected', 'Removed by coach'), ('undone', 'Undone')])
    skill_result = models.OneToOneField('skill_tracker.SkillResult', on_delete=models.SET_NULL, null=True, blank=True, related_name='engagement_record')
    routine_result = models.OneToOneField('routine_tracker.DailyRoutineAttempt', on_delete=models.SET_NULL, null=True, blank=True, related_name='engagement_record')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['gym', 'status', 'practice_date'], name='tracker_review_lookup')]


class AthleteFeedback(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    private_notes = models.TextField(max_length=3000, blank=True)
    shared_feedback = models.TextField(max_length=3000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class PersonalMilestone(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    key = models.CharField(max_length=180)
    title = models.CharField(max_length=150)
    details = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    awarded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    practice_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'key'], name='unique_personal_tracker_milestone')]
        ordering = ['-practice_date', '-pk']


class WeeklyProgressSummary(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    week_start = models.DateField()
    snapshot = models.JSONField(default=dict)
    coach_feedback = models.TextField(max_length=3000, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'coach', 'week_start'], name='unique_coach_athlete_weekly_summary')]
        ordering = ['-week_start', '-pk']
