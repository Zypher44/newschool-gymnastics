


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
    soreness = models.PositiveSmallIntegerField(choices=SCORE_CHOICES, default=3, null=True, blank=True)
    stress = models.PositiveSmallIntegerField(choices=SCORE_CHOICES, default=3, null=True, blank=True)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    ate_well = models.BooleanField(default=False)
    hydrated = models.BooleanField(default=False)

    soreness_area = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    checkin_version = models.PositiveSmallIntegerField(default=1)
    sleep_quality = models.CharField(max_length=12, blank=True, choices=[('well', 'Well'), ('okay', 'Okay'), ('poor', 'Poorly')])
    body_feeling = models.CharField(max_length=12, blank=True, choices=[('good', 'Good'), ('sore', 'Sore muscles'), ('pain', 'Something hurts'), ('sick', 'I feel sick')])
    practice_feeling = models.CharField(max_length=12, blank=True, choices=[('excited', 'Excited'), ('okay', 'Okay'), ('nervous', 'Nervous'), ('upset', 'Upset')])
    help_event = models.CharField(max_length=12, blank=True, choices=[('none', 'Nothing specific'), ('vault', 'Vault'), ('bars', 'Bars'), ('beam', 'Beam'), ('floor', 'Floor')])
    help_skill = models.ForeignKey('skill_tracker.Assignment', null=True, blank=True, on_delete=models.SET_NULL, related_name='checkins')
    help_kind = models.CharField(max_length=15, blank=True, choices=[('reminder', 'A reminder'), ('demo', 'A demonstration'), ('confidence', 'Help feeling confident'), ('talk', 'Talk to my coach')])
    coach_talk = models.CharField(max_length=12, blank=True, choices=[('before', 'Yes, before practice'), ('later', "Yes, when there's time"), ('no', 'No thanks')])
    told_coach = models.CharField(max_length=8, blank=True, choices=[('yes', 'Yes'), ('no', 'Not yet')])
    worry_about = models.CharField(max_length=12, blank=True, choices=[('skill', 'A skill'), ('event', 'An event'), ('other', 'Something else'), ('private', "I'd rather tell my coach")])

    @property
    def checkin_flags(self):
        if self.checkin_version < 2:
            return []
        flags = []
        if self.body_feeling in ('pain', 'sick') or self.coach_talk == 'before':
            flags.append('Talk before practice')
        if self.energy <= 2:
            flags.append('Low energy')
        if self.sleep_quality == 'poor':
            flags.append('Poor sleep')
        if self.body_feeling == 'sore':
            flags.append('Sore muscles')
        if self.practice_feeling in ('nervous', 'upset'):
            flags.append('Needs encouragement')
        if self.help_event not in ('', 'none') or self.help_skill_id:
            flags.append('Skill help requested')
        if self.coach_talk == 'later':
            flags.append('Private check-in requested')
        return flags or ['Ready to start']

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('athlete', 'survey_date')
        ordering = ['-survey_date', '-created_at']

    def save(self, *args, **kwargs):
        if self.athlete.role != 'athlete':
            raise ValidationError('Survey must belong to a user with athlete role.')

        for value in [self.energy, self.soreness, self.stress]:
            if value is not None and (value < 1 or value > 5):
                raise ValidationError('Energy, soreness, and stress must be between 1 and 5.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.survey_date}"