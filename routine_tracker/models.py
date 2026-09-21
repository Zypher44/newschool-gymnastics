from django.conf import settings
from django.db import models


class DailyRoutineSession(models.Model):
    practice_date = models.DateField(
        unique=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_daily_routine_sessions',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            '-practice_date',
        ]

    def __str__(self):
        return (
            f'Routine Tracker - '
            f'{self.practice_date}'
        )


class DailyRoutineAttempt(models.Model):
    EVENT_VAULT = 'vault'
    EVENT_BARS = 'bars'
    EVENT_BEAM = 'beam'
    EVENT_FLOOR = 'floor'

    EVENT_CHOICES = [
        (EVENT_VAULT, 'Vault'),
        (EVENT_BARS, 'Bars'),
        (EVENT_BEAM, 'Beam'),
        (EVENT_FLOOR, 'Floor'),
    ]

    RESULT_WOW = 'wow'
    RESULT_HIT = 'hit'
    RESULT_MISSED = 'missed'

    RESULT_CHOICES = [
        (RESULT_WOW, 'Wow'),
        (RESULT_HIT, 'Hit'),
        (RESULT_MISSED, 'Miss'),
    ]

    session = models.ForeignKey(
        DailyRoutineSession,
        on_delete=models.CASCADE,
        related_name='attempts',
    )

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_routine_attempts',
        limit_choices_to={
            'role': 'athlete',
        },
    )

    event = models.CharField(
        max_length=20,
        choices=EVENT_CHOICES,
    )

    attempt_number = models.PositiveIntegerField(
        default=1,
    )

    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
    )

    notes = models.CharField(
        max_length=250,
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_routine_attempts',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            'athlete__first_name',
            'athlete__last_name',
            'event',
            'attempt_number',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'session',
                    'athlete',
                    'event',
                    'attempt_number',
                ],
                name='unique_daily_routine_attempt',
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    'athlete',
                    'event',
                    'created_at',
                ],
            ),
        ]

    def __str__(self):
        return (
            f'{self.athlete} - '
            f'{self.get_event_display()} '
            f'#{self.attempt_number} - '
            f'{self.get_result_display()}'
        )
