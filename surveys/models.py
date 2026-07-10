


# Create your models here.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DailySurvey(models.Model):
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_surveys'
    )
    survey_date = models.DateField()
    SCORE_CHOICES = [
        (1, '1 - Very Low'),
        (2, '2 - Low'),
        (3, '3 - Okay'),
        (4, '4 - Good'),
        (5, '5 - Great'),
    ]
    energy = models.PositiveSmallIntegerField(choices=SCORE_CHOICES, default=3)
    soreness = models.PositiveSmallIntegerField(choices=SCORE_CHOICES, default=3)
    stress = models.PositiveSmallIntegerField(choices=SCORE_CHOICES, default=3)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    ate_well = models.BooleanField(default=False)
    hydrated = models.BooleanField(default=False)

    soreness_area = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('athlete', 'survey_date')
        ordering = ['-survey_date', '-created_at']

    def save(self, *args, **kwargs):
        if self.athlete.role != 'athlete':
            raise ValidationError('Survey must belong to a user with athlete role.')

        for value in [self.energy, self.soreness, self.stress]:
            if value < 1 or value > 5:
                raise ValidationError('Energy, soreness, and stress must be between 1 and 5.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.survey_date}"