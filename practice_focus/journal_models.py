from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from gyms.models import GymMembership


class AthleteJournalEntry(models.Model):
    MOODS = [('great', 'Great'), ('okay', 'Okay'), ('tough', 'Tough')]
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='practice_journal_entries')
    entry_date = models.DateField()
    mood = models.CharField(max_length=10, choices=MOODS, blank=True)
    win = models.TextField(max_length=1500, blank=True)
    challenge = models.TextField(max_length=1500, blank=True)
    next_focus = models.TextField(max_length=1500, blank=True)
    share_with_coaches = models.BooleanField(default=False)
    share_with_parents = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-pk']
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'entry_date'],
            name='unique_athlete_journal_day')]

    def clean(self):
        super().clean()
        if self.entry_date and self.entry_date > timezone.localdate():
            raise ValidationError({'entry_date': 'Choose today or an earlier date.'})
        if not any(str(value or '').strip() for value in
                   (self.mood, self.win, self.challenge, self.next_focus)):
            raise ValidationError('Choose how practice felt or answer one question before saving.')
        if self.gym_id and self.athlete_id and not GymMembership.objects.filter(
            gym_id=self.gym_id, gym__is_active=True, user_id=self.athlete_id,
            user__is_active=True, user__role='athlete', role='athlete', is_active=True).exists():
            raise ValidationError('Journal entries must belong to an active athlete in this gym.')

    @property
    def audience_label(self):
        if self.share_with_coaches and self.share_with_parents:
            return 'Shared with coaches and parents'
        if self.share_with_coaches:
            return 'Shared with coaches'
        if self.share_with_parents:
            return 'Shared with parents'
        return 'Only me'

    def __str__(self):
        return f'{self.athlete_id} · Practice journal · {self.entry_date}'
