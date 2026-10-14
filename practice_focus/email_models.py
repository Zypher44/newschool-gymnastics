from uuid import uuid4
from django.conf import settings
from django.db import models


class EmailReportDraft(models.Model):
    gym = models.ForeignKey('gyms.Gym', on_delete=models.CASCADE)
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    report_key = models.CharField(max_length=20)
    fingerprint = models.CharField(max_length=64)
    snapshot = models.JSONField(default=dict)
    weekly_summary = models.ForeignKey('practice_focus.WeeklyProgressSummary', on_delete=models.CASCADE, null=True, blank=True)
    publication = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['gym', 'coach', 'fingerprint'], name='unique_email_report_preview')]
        ordering = ['-created_at', '-pk']


class ReportEmailDelivery(models.Model):
    draft = models.ForeignKey(EmailReportDraft, on_delete=models.CASCADE, related_name='deliveries')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    email = models.EmailField()
    token = models.UUIDField(default=uuid4, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='ready', choices=[
        ('ready', 'Ready'), ('sending', 'Sending'), ('submitted', 'Submitted to email provider'),
        ('failed', 'Not sent'), ('unconfirmed', 'Confirmation pending'), ('blocked', 'Needs a new preview')])
    first_attempt = models.DateTimeField(null=True, blank=True)
    last_attempt = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    provider_id = models.CharField(max_length=160, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    may_have_sent = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['draft', 'email'], name='unique_report_email_address')]
        ordering = ['pk']
