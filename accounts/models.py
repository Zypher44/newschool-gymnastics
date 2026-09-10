from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = [
        ('admin', 'Platform Admin'),
        ('director', 'Gym Director'),
        ('head_coach', 'Head Coach'),
        ('coach', 'Coach'),
        ('athlete', 'Athlete'),
        ('parent', 'Parent'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return (
            self.get_full_name()
            or self.username
        )