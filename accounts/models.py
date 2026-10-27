from uuid import uuid4
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

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    def __str__(self):
        return (
            self.get_full_name()
            or self.username
        )


class CommunicationPreference(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='communication_preference')
    in_app_updates = models.BooleanField(default=True)
    email_reports = models.BooleanField(default=True)
    report_frequency = models.CharField(max_length=12, default='immediate', choices=[('immediate', 'When a coach sends a report'), ('weekly', 'Weekly summary')])
    last_digest_at = models.DateTimeField(null=True, blank=True)


class QueuedParentReport(models.Model):
    parent = models.ForeignKey('User', on_delete=models.CASCADE)
    draft = models.ForeignKey('practice_focus.EmailReportDraft', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    batch = models.ForeignKey('ParentReportDigest', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['parent', 'draft'], name='unique_parent_report_queue')]


class ParentReportDigest(models.Model):
    parent = models.ForeignKey('User', on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid4, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)


class PublicEnquiry(models.Model):
    """Product enquiries, kept separate from gym and athlete information."""

    class Kind(models.TextChoices):
        DEMO = 'demo', 'A gym demo'
        PRICING = 'pricing', 'Pricing or a pilot'
        SUPPORT = 'support', 'Product support'
        PRIVACY = 'privacy', 'A privacy or data request'

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        CONTACTED = 'contacted', 'Contacted'
        CLOSED = 'closed', 'Closed'

    submission_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    gym_name = models.CharField(max_length=160, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    message = models.TextField(max_length=2000, blank=True)
    consent_to_reply = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_kind_display()} — {self.gym_name or self.name}'
