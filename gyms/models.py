from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Gym(models.Model):
    name = models.CharField(max_length=150)

    address = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    province_state = models.CharField(
        max_length=100,
        blank=True
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        default='Canada'
    )

    phone = models.CharField(
        max_length=30,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GymMembership(models.Model):
    ROLE_CHOICES = [
        ('director', 'Director'),
        ('head_coach', 'Head Coach'),
        ('coach', 'Coach'),
        ('athlete', 'Athlete'),
        ('parent', 'Parent'),
    ]

    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gym_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    is_active = models.BooleanField(
        default=True
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'gym',
                    'user',
                    'role'
                ],
                name='unique_gym_user_role'
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.gym.name} - "
            f"{self.get_role_display()}"
        )


class TrainingGroup(models.Model):
    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name='training_groups'
    )

    name = models.CharField(
        max_length=150
    )

    description = models.TextField(
        blank=True
    )

    level = models.CharField(
        max_length=100,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            'gym__name',
            'name'
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'gym',
                    'name'
                ],
                name='unique_training_group_per_gym'
            )
        ]

    def __str__(self):
        return (
            f"{self.gym.name} - "
            f"{self.name}"
        )


class TrainingGroupCoach(models.Model):
    COACH_ROLE_CHOICES = [
        ('head_coach', 'Head Coach'),
        ('coach', 'Coach'),
        ('assistant', 'Assistant Coach'),
    ]

    group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.CASCADE,
        related_name='coach_assignments'
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_group_assignments'
    )

    role = models.CharField(
        max_length=20,
        choices=COACH_ROLE_CHOICES,
        default='coach'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'group',
                    'coach'
                ],
                name='unique_group_coach'
            )
        ]

    def clean(self):
        valid_membership = GymMembership.objects.filter(
            gym=self.group.gym,
            user=self.coach,
            role__in=[
                'director',
                'head_coach',
                'coach'
            ],
            is_active=True
        ).exists()

        if not valid_membership:
            raise ValidationError(
                'Coach must be an active staff member '
                'of this gym.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.group.name} - "
            f"{self.coach.username}"
        )


class TrainingGroupAthlete(models.Model):
    group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.CASCADE,
        related_name='athlete_assignments'
    )

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_groups'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'group',
                    'athlete'
                ],
                name='unique_group_athlete'
            )
        ]

    def clean(self):
        valid_membership = GymMembership.objects.filter(
            gym=self.group.gym,
            user=self.athlete,
            role='athlete',
            is_active=True
        ).exists()

        if not valid_membership:
            raise ValidationError(
                'Athlete must be an active athlete '
                'at this gym.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.group.name} - "
            f"{self.athlete.username}"
        )


from django.db import models

# Create your models here.
