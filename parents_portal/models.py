from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ParentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile',
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    def clean(self):
        super().clean()

        if self.user_id and self.user.role != 'parent':
            raise ValidationError(
                {'user': 'User must have the parent role.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'Parent: '
            f'{self.user.get_full_name() or self.user.username}'
        )


class ParentAthleteLink(models.Model):
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='linked_athletes',
    )

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='linked_parents',
    )

    relationship = models.CharField(
        max_length=50,
        blank=True,
    )

    approved = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'athlete'],
                name='unique_parent_athlete_link',
            ),
            models.CheckConstraint(
                condition=~models.Q(parent=models.F('athlete')),
                name='parent_cannot_link_to_self',
            ),
        ]

        indexes = [
            models.Index(
                fields=['parent', 'approved'],
                name='parent_link_access_idx',
            ),
            models.Index(
                fields=['athlete', 'approved'],
                name='athlete_link_access_idx',
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.parent_id and self.parent.role != 'parent':
            errors['parent'] = 'Parent must have the parent role.'

        if self.athlete_id and self.athlete.role != 'athlete':
            errors['athlete'] = 'Athlete must have the athlete role.'

        if (
            self.parent_id
            and self.athlete_id
            and self.parent_id == self.athlete_id
        ):
            errors['athlete'] = 'A parent cannot be linked to themselves.'

        if self.parent_id and self.athlete_id:
            from gyms.models import GymMembership

            parent_gym_ids = (
                GymMembership.objects
                .filter(
                    user_id=self.parent_id,
                    role='parent',
                    is_active=True,
                    gym__is_active=True,
                )
                .values_list('gym_id', flat=True)
            )

            shares_active_gym = (
                GymMembership.objects
                .filter(
                    user_id=self.athlete_id,
                    role='athlete',
                    is_active=True,
                    gym__is_active=True,
                    gym_id__in=parent_gym_ids,
                )
                .exists()
            )

            if not shares_active_gym:
                errors['athlete'] = (
                    'Parent and athlete must belong to the same active gym.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.parent.username} -> {self.athlete.username}'


class PracticeAbsenceNotice(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_absence_notices')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_absence_notices')
    practice_date = models.DateField()
    event = models.ForeignKey('coaches.TeamEvent', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=[('absent', 'Absent'), ('late', 'Arriving late'), ('cancelled', 'Cancelled')])
    expected_arrival = models.TimeField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['athlete', 'practice_date'], name='unique_child_practice_notice')]
        ordering = ['practice_date', 'athlete_id']
