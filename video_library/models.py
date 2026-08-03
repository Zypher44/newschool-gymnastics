import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def video_upload_path(
    instance,
    filename,
):
    """
    Store videos using non-identifying UUID filenames.

    The same upload path will work with local storage during
    development and Cloudflare R2 in production.
    """

    extension = (
        Path(filename).suffix.lower()
        or '.mp4'
    )

    current_date = timezone.localdate()

    return (
        f'videos/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}{extension}'
    )


def thumbnail_upload_path(
    instance,
    filename,
):
    extension = (
        Path(filename).suffix.lower()
        or '.jpg'
    )

    current_date = timezone.localdate()

    return (
        f'video-thumbnails/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}{extension}'
    )


class Video(models.Model):
    EVENT_VAULT = 'vault'
    EVENT_BARS = 'bars'
    EVENT_BEAM = 'beam'
    EVENT_FLOOR = 'floor'
    EVENT_TRAMPOLINE = 'trampoline'
    EVENT_STRENGTH = 'strength'
    EVENT_CONDITIONING = 'conditioning'
    EVENT_FLEXIBILITY = 'flexibility'
    EVENT_DANCE = 'dance'
    EVENT_OTHER = 'other'

    EVENT_CHOICES = [
        (
            EVENT_VAULT,
            'Vault',
        ),
        (
            EVENT_BARS,
            'Bars',
        ),
        (
            EVENT_BEAM,
            'Beam',
        ),
        (
            EVENT_FLOOR,
            'Floor',
        ),
        (
            EVENT_TRAMPOLINE,
            'Trampoline',
        ),
        (
            EVENT_STRENGTH,
            'Strength',
        ),
        (
            EVENT_CONDITIONING,
            'Conditioning',
        ),
        (
            EVENT_FLEXIBILITY,
            'Flexibility',
        ),
        (
            EVENT_DANCE,
            'Dance',
        ),
        (
            EVENT_OTHER,
            'Other',
        ),
    ]

    TYPE_PRACTICE = 'practice'
    TYPE_COMPETITION = 'competition'
    TYPE_TESTING = 'testing'
    TYPE_DRILL = 'drill'
    TYPE_ROUTINE = 'routine'
    TYPE_PROGRESS = 'progress'
    TYPE_OTHER = 'other'

    VIDEO_TYPE_CHOICES = [
        (
            TYPE_PRACTICE,
            'Practice',
        ),
        (
            TYPE_COMPETITION,
            'Competition',
        ),
        (
            TYPE_TESTING,
            'Performance Testing',
        ),
        (
            TYPE_DRILL,
            'Drill',
        ),
        (
            TYPE_ROUTINE,
            'Routine',
        ),
        (
            TYPE_PROGRESS,
            'Progress Video',
        ),
        (
            TYPE_OTHER,
            'Other',
        ),
    ]

    VISIBILITY_COACHES = 'coaches'
    VISIBILITY_ATHLETE = 'athlete'
    VISIBILITY_PARENTS = 'parents'
    VISIBILITY_PRIVATE = 'private'

    VISIBILITY_CHOICES = [
        (
            VISIBILITY_COACHES,
            'Coaches Only',
        ),
        (
            VISIBILITY_ATHLETE,
            'Coaches and Athlete',
        ),
        (
            VISIBILITY_PARENTS,
            'Coaches, Athlete and Parents',
        ),
        (
            VISIBILITY_PRIVATE,
            'Uploader Only',
        ),
    ]

    STATUS_UPLOADING = 'uploading'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (
            STATUS_UPLOADING,
            'Uploading',
        ),
        (
            STATUS_READY,
            'Ready',
        ),
        (
            STATUS_FAILED,
            'Upload Failed',
        ),
        (
            STATUS_ARCHIVED,
            'Archived',
        ),
    ]

    AI_NOT_REQUESTED = 'not_requested'
    AI_QUEUED = 'queued'
    AI_PROCESSING = 'processing'
    AI_COMPLETED = 'completed'
    AI_FAILED = 'failed'

    AI_STATUS_CHOICES = [
        (
            AI_NOT_REQUESTED,
            'Not Requested',
        ),
        (
            AI_QUEUED,
            'Queued',
        ),
        (
            AI_PROCESSING,
            'Processing',
        ),
        (
            AI_COMPLETED,
            'Completed',
        ),
        (
            AI_FAILED,
            'Failed',
        ),
    ]

    title = models.CharField(
        max_length=180,
    )

    video_file = models.FileField(
        upload_to=video_upload_path,
    )

    thumbnail = models.ImageField(
        upload_to=thumbnail_upload_path,
        null=True,
        blank=True,
    )

    primary_athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='primary_gymnastics_videos',
        null=True,
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
    )

    tagged_athletes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='tagged_gymnastics_videos',
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
        help_text=(
            'Use this when more than one athlete appears '
            'in the video.'
        ),
    )

    training_group = models.ForeignKey(
        'practice_planner.TrainingGroup',
        on_delete=models.SET_NULL,
        related_name='videos',
        null=True,
        blank=True,
    )

    practice_plan = models.ForeignKey(
        'practice_planner.PracticePlan',
        on_delete=models.SET_NULL,
        related_name='videos',
        null=True,
        blank=True,
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
        default=EVENT_OTHER,
    )

    skill_name = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            'Examples: Jager, Pak salto, beam series, '
            'Yurchenko layout.'
        ),
    )

    video_type = models.CharField(
        max_length=30,
        choices=VIDEO_TYPE_CHOICES,
        default=TYPE_PRACTICE,
    )

    recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            'When the video was recorded. If unknown, '
            'the upload time will still be saved.'
        ),
    )

    notes = models.TextField(
        blank=True,
    )

    tags = models.CharField(
        max_length=300,
        blank=True,
        help_text=(
            'Separate tags with commas. Example: '
            'release, competition routine, personal best'
        ),
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_COACHES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_READY,
    )

    is_favorite = models.BooleanField(
        default=False,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='uploaded_gymnastics_videos',
        null=True,
        blank=True,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    file_size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    content_type = models.CharField(
        max_length=100,
        blank=True,
    )

    ai_status = models.CharField(
        max_length=30,
        choices=AI_STATUS_CHOICES,
        default=AI_NOT_REQUESTED,
    )

    ai_summary = models.TextField(
        blank=True,
    )

    ai_results = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Structured AI results such as detected skills, '
            'body angles, deductions, and confidence scores.'
        ),
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            '-recorded_at',
            '-uploaded_at',
        ]

        indexes = [
            models.Index(
                fields=[
                    'event',
                    'skill_name',
                ],
                name='video_event_skill_idx',
            ),
            models.Index(
                fields=[
                    'status',
                    'uploaded_at',
                ],
                name='video_status_date_idx',
            ),
            models.Index(
                fields=[
                    'ai_status',
                ],
                name='video_ai_status_idx',
            ),
        ]

    def __str__(self):
        athlete_name = 'Unassigned'

        if self.primary_athlete:
            athlete_name = (
                self.primary_athlete.get_full_name().strip()
                or self.primary_athlete.username
            )

        return (
            f'{self.title} - '
            f'{athlete_name}'
        )

    def clean(self):
        errors = {}

        if (
            self.primary_athlete_id
            and self.primary_athlete.role != 'athlete'
        ):
            errors['primary_athlete'] = (
                'The primary athlete must have the athlete role.'
            )

        if (
            self.practice_plan_id
            and self.training_group_id
            and self.practice_plan.training_group_id
            != self.training_group_id
        ):
            errors['training_group'] = (
                'The selected training group must match the '
                'practice training group.'
            )

        if errors:
            raise ValidationError(errors)

    def save(
        self,
        *args,
        **kwargs,
    ):
        if self.video_file:
            if not self.original_filename:
                self.original_filename = (
                    Path(self.video_file.name).name
                )

            try:
                self.file_size_bytes = (
                    self.video_file.size
                )
            except (
                AttributeError,
                OSError,
            ):
                pass

        super().save(
            *args,
            **kwargs,
        )

    @property
    def file_size_mb(self):
        if not self.file_size_bytes:
            return None

        return round(
            self.file_size_bytes
            / 1024
            / 1024,
            1,
        )

    @property
    def formatted_duration(self):
        if self.duration_seconds is None:
            return ''

        minutes, seconds = divmod(
            self.duration_seconds,
            60,
        )

        hours, minutes = divmod(
            minutes,
            60,
        )

        if hours:
            return (
                f'{hours}:'
                f'{minutes:02d}:'
                f'{seconds:02d}'
            )

        return (
            f'{minutes}:'
            f'{seconds:02d}'
        )

    @property
    def tag_list(self):
        if not self.tags:
            return []

        return [
            tag.strip()
            for tag in self.tags.split(',')
            if tag.strip()
        ]


class VideoReview(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_IN_REVIEW = 'in_review'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (
            STATUS_PENDING,
            'Pending',
        ),
        (
            STATUS_IN_REVIEW,
            'In Review',
        ),
        (
            STATUS_COMPLETED,
            'Completed',
        ),
    ]

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    assigned_coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_video_reviews',
        null=True,
        blank=True,
        limit_choices_to={
            'role__in': [
                'coach',
                'head_coach',
            ],
        },
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='requested_video_reviews',
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    coach_feedback = models.TextField(
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            'status',
            '-requested_at',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'video',
                    'assigned_coach',
                ],
                name='unique_video_review_per_coach',
            ),
        ]

    def __str__(self):
        return (
            f'{self.video.title} - '
            f'{self.get_status_display()}'
        )