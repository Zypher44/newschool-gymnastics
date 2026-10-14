from django.conf import settings
from django.db import models
from practice_focus.models import EVENTS

class Skill(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    event = models.CharField(max_length=20, choices=EVENTS)
    name = models.CharField(max_length=150)
    key = models.CharField(max_length=450)

    class Meta:
        ordering = ['event', 'name', 'pk']
        constraints = [models.UniqueConstraint(fields=['gym', 'event', 'key'], name='unique_tracker_skill')]

    def __str__(self):
        return self.name

class Assignment(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['skill', 'athlete'], name='unique_tracker_assignment')]

class SkillResult(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name='results')
    result = models.CharField(max_length=10, choices=[('wow', 'Wow'), ('hit', 'Hit'), ('missed', 'Attempt')])
    practice_date = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    token = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
