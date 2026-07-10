from django.db import models

# Create your models here.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ParentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    phone = models.CharField(max_length=30, blank=True)

    def save(self, *args, **kwargs):
        if self.user.role != 'parent':
            raise ValidationError('User must have parent role.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Parent: {self.user.get_full_name() or self.user.username}"


class ParentAthleteLink(models.Model):
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='linked_athletes'
    )
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='linked_parents'
    )
    relationship = models.CharField(max_length=50, blank=True)
    approved = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.parent.role != 'parent':
            raise ValidationError('Parent must have parent role.')
        if self.athlete.role != 'athlete':
            raise ValidationError('Athlete must have athlete role.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent.username} -> {self.athlete.username}"