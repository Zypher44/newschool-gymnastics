from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class AthleteProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athlete_profile'
    )

    date_of_birth = models.DateField(null=True, blank=True)
    level = models.CharField(max_length=100, blank=True)
    team_name = models.CharField(max_length=100, blank=True)
    training_group = models.CharField(max_length=100, blank=True)

    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    medical_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.user.role.lower() != 'athlete':
            raise ValidationError('User must have athlete role.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Athlete: {self.user.get_full_name() or self.user.username}"


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_taken'
    )

    attendance_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='present'
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('athlete', 'attendance_date')
        ordering = ['-attendance_date', 'athlete__username']

    def save(self, *args, **kwargs):
        if self.athlete.role.lower() != 'athlete':
            raise ValidationError('Attendance must be attached to an athlete.')

        if self.coach and self.coach.role not in ['coach', 'head_coach']:
            raise ValidationError('Attendance must be taken by a coach.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.attendance_date} - {self.status}"


class Skill(models.Model):
    EVENT_CHOICES = [
        ('vault', 'Vault'),
        ('bars', 'Bars'),
        ('beam', 'Beam'),
        ('floor', 'Floor'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
    ]

    name = models.CharField(max_length=100)
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['event', 'name']
        unique_together = ('name', 'event')

    def __str__(self):
        return f"{self.get_event_display()} - {self.name}"


class AthleteSkill(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('consistent', 'Consistent'),
        ('competition_ready', 'Competition Ready'),
        ('mastered', 'Mastered'),
    ]

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athlete_skills'
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='athlete_progress'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='not_started'
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skills_updated'
    )

    started_date = models.DateField(null=True, blank=True)
    achieved_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('athlete', 'skill')
        ordering = ['skill__event', 'skill__name']

    def save(self, *args, **kwargs):
        if self.athlete.role.lower() != 'athlete':
            raise ValidationError('Skill progress must be attached to an athlete.')

        if self.coach and self.coach.role not in ['coach', 'head_coach']:
            raise ValidationError('Skill progress must be updated by a coach.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.skill.name} - {self.get_status_display()}"


class AthleteVideo(models.Model):
    EVENT_CHOICES = [
        ('vault', 'Vault'),
        ('bars', 'Bars'),
        ('beam', 'Beam'),
        ('floor', 'Floor'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
        ('other', 'Other'),
    ]

    REVIEW_STATUS_CHOICES = [
        ('not_reviewed', 'Not Reviewed'),
        ('reviewed', 'Reviewed'),
        ('needs_follow_up', 'Needs Follow-Up'),
        ('highlight', 'Highlight'),
    ]

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athlete_videos'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_videos'
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
        default='other'
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='videos'
    )

    title = models.CharField(max_length=150)
    attempt_number = models.PositiveIntegerField(null=True, blank=True)
    practice_date = models.DateField(null=True, blank=True)

    video_file = models.FileField(upload_to='athlete_videos/')

    technical_focus = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    coach_feedback = models.TextField(blank=True)

    review_status = models.CharField(
        max_length=30,
        choices=REVIEW_STATUS_CHOICES,
        default='not_reviewed'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-practice_date', '-attempt_number', '-uploaded_at']

    def save(self, *args, **kwargs):
        if self.athlete.role.lower() != 'athlete':
            raise ValidationError('Video must be attached to an athlete.')

        if self.uploaded_by and self.uploaded_by.role not in ['coach', 'head_coach', 'athlete']:
            raise ValidationError('Video must be uploaded by a coach, head coach, or athlete.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.title}"

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athlete_videos'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_videos'
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
        default='other'
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='videos'
    )

    title = models.CharField(max_length=150)
    practice_date = models.DateField(null=True, blank=True)
    video_file = models.FileField(upload_to='athlete_videos/')
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-practice_date', '-uploaded_at']

    def save(self, *args, **kwargs):
        if self.athlete.role.lower() != 'athlete':
            raise ValidationError('Video must be attached to an athlete.')

        if self.uploaded_by and self.uploaded_by.role not in ['coach', 'head_coach', 'athlete']:
            raise ValidationError('Video must be uploaded by a coach, head coach, or athlete.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.athlete.username} - {self.title}"


@receiver(post_save, sender=Skill)
def create_athlete_skills_for_new_skill(sender, instance, created, **kwargs):
    if created:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        athletes = User.objects.filter(role='athlete')

        for athlete in athletes:
            AthleteSkill.objects.get_or_create(
                athlete=athlete,
                skill=instance,
                defaults={
                    'status': 'not_started'
                }
            )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_skills_for_new_athlete(sender, instance, created, **kwargs):
    if instance.role == 'athlete':
        skills = Skill.objects.all()

        for skill in skills:
            AthleteSkill.objects.get_or_create(
                athlete=instance,
                skill=skill,
                defaults={
                    'status': 'not_started'
                }
            )

