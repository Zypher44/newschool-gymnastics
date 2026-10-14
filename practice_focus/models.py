from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

EVENTS = [('vault', 'Vault'), ('bars', 'Bars'), ('beam', 'Beam'), ('floor', 'Floor')]


class EventSkillPlan(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE, related_name='current_skill_plans')
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='current_skill_plans')
    event = models.CharField(max_length=20, choices=EVENTS)
    skills_text = models.TextField(blank=True, max_length=8000)
    training_cues = models.TextField(blank=True, max_length=1000)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_skill_plans')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event', 'pk']
        constraints = [models.UniqueConstraint(fields=['gym', 'athlete', 'event'], name='unique_current_skills_per_event')]

    @property
    def skill_names(self):
        return [line.strip() for line in self.skills_text.splitlines() if line.strip()]

    def clean(self):
        from gyms.models import GymMembership
        super().clean()
        if self.gym_id and self.athlete_id and not GymMembership.objects.filter(
            gym_id=self.gym_id, gym__is_active=True, user_id=self.athlete_id,
            user__role='athlete', user__is_active=True, role='athlete', is_active=True,
        ).exists():
            raise ValidationError({'athlete': 'Choose an active athlete in this gym.'})
        if self.updated_by_id and self.gym_id and not GymMembership.objects.filter(
            gym_id=self.gym_id, user_id=self.updated_by_id, user__is_active=True,
            user__role__in=['coach', 'head_coach'], role__in=['coach', 'head_coach'], is_active=True,
        ).exists():
            raise ValidationError({'updated_by': 'Only active coaches in this gym can update these skills.'})

    def __str__(self):
        return f'{self.athlete} · {self.get_event_display()} · {self.gym}'


# V3 individual practice plans
from .personal_models import AthletePracticePlan, PracticePlanTemplate

# V3 coach report preferences
from .report_models import CoachReportPreference

# V3 practice progress upgrades
from .engagement_models import TrackerMutation, TrackedResult, AthleteFeedback, PersonalMilestone, WeeklyProgressSummary

# V3 report email delivery
from .email_models import EmailReportDraft, ReportEmailDelivery

# V3 Practice Passport
from .passport_models import PassportStamp, PassportAction

# V3 coach badge library
from .passport_badge_models import PassportBadgeDefinition

# V3 dated athlete practice journal
from .journal_models import AthleteJournalEntry
