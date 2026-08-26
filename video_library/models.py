import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ============================================================
# FILE PATH HELPERS
# ============================================================


def video_upload_path(
    instance,
    filename,
):
    extension = (
        Path(filename).suffix.lower()
        or '.mp4'
    )

    current_date = (
        timezone.localdate()
    )

    return (
        f'videos/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}'
        f'{extension}'
    )


def thumbnail_upload_path(
    instance,
    filename,
):
    extension = (
        Path(filename).suffix.lower()
        or '.jpg'
    )

    current_date = (
        timezone.localdate()
    )

    return (
        f'video-thumbnails/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}'
        f'{extension}'
    )


def analysis_video_upload_path(
    instance,
    filename,
):
    extension = (
        Path(filename).suffix.lower()
        or '.mp4'
    )

    current_date = (
        timezone.localdate()
    )

    return (
        f'video-analysis/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}'
        f'{extension}'
    )


def analysis_frame_upload_path(
    instance,
    filename,
):
    extension = (
        Path(filename).suffix.lower()
        or '.jpg'
    )

    current_date = (
        timezone.localdate()
    )

    return (
        f'video-analysis-frames/'
        f'{current_date:%Y/%m}/'
        f'{uuid.uuid4().hex}'
        f'{extension}'
    )


# ============================================================
# VIDEO
# ============================================================


class Video(models.Model):

    # --------------------------------------------------------
    # EVENT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VIDEO TYPE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VISIBILITY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VIDEO STATUS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # AI STATUS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CORE VIDEO FIELDS
    # --------------------------------------------------------

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
        related_name=(
            'primary_gymnastics_videos'
        ),
        null=True,
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
    )

    tagged_athletes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name=(
            'tagged_gymnastics_videos'
        ),
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
        help_text=(
            'Use this when more than one '
            'athlete appears in the video.'
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
            'Examples: Handstand, Jager, '
            'Pak salto, beam series.'
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
            'When the video was recorded.'
        ),
    )

    notes = models.TextField(
        blank=True,
    )

    tags = models.CharField(
        max_length=300,
        blank=True,
        help_text=(
            'Separate tags with commas.'
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

    # --------------------------------------------------------
    # 3.7T COACHING REFERENCE FIELDS
    # --------------------------------------------------------

    is_personal_best = models.BooleanField(
        default=False,
    )

    is_reference_attempt = (
        models.BooleanField(
            default=False,
        )
    )

    is_coaching_example = (
        models.BooleanField(
            default=False,
        )
    )

    reference_marked_by = (
        models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            related_name=(
                'marked_reference_videos'
            ),
            null=True,
            blank=True,
        )
    )

    reference_marked_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    # --------------------------------------------------------
    # FILE / UPLOAD INFORMATION
    # --------------------------------------------------------

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            'uploaded_gymnastics_videos'
        ),
        null=True,
        blank=True,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    file_size_bytes = (
        models.PositiveBigIntegerField(
            null=True,
            blank=True,
        )
    )

    duration_seconds = (
        models.PositiveIntegerField(
            null=True,
            blank=True,
        )
    )

    content_type = models.CharField(
        max_length=100,
        blank=True,
    )

    # --------------------------------------------------------
    # AI RESULTS
    # --------------------------------------------------------

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
            'Structured AI results such as '
            'detected skills, body angles, '
            'deductions and confidence scores.'
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
                name=(
                    'video_event_skill_idx'
                ),
            ),

            models.Index(
                fields=[
                    'status',
                    'uploaded_at',
                ],
                name=(
                    'video_status_date_idx'
                ),
            ),

            models.Index(
                fields=[
                    'ai_status',
                ],
                name='video_ai_status_idx',
            ),

            models.Index(
                fields=[
                    'primary_athlete',
                    'skill_name',
                    'is_reference_attempt',
                ],
                name=(
                    'video_reference_idx'
                ),
            ),
        ]

    def __str__(
        self,
    ):
        athlete_name = (
            'Unassigned'
        )

        if self.primary_athlete:

            athlete_name = (
                self.primary_athlete
                .get_full_name()
                .strip()
                or
                self.primary_athlete
                .username
            )

        return (
            f'{self.title} - '
            f'{athlete_name}'
        )

    def clean(
        self,
    ):
        errors = {}

        if (
            self.primary_athlete_id
            and
            self.primary_athlete.role
            != 'athlete'
        ):
            errors[
                'primary_athlete'
            ] = (
                'The primary athlete must '
                'have the athlete role.'
            )

        if (
            self.practice_plan_id
            and self.training_group_id
            and
            self.practice_plan
            .training_group_id
            !=
            self.training_group_id
        ):
            errors[
                'training_group'
            ] = (
                'The selected training group '
                'must match the practice '
                'training group.'
            )

        if (
            self.is_reference_attempt
            and
            not self.primary_athlete_id
        ):
            errors[
                'is_reference_attempt'
            ] = (
                'A reference attempt requires '
                'a primary athlete.'
            )

        if (
            self.is_reference_attempt
            and not (
                self.skill_name
                or ''
            ).strip()
        ):
            errors[
                'skill_name'
            ] = (
                'A reference attempt requires '
                'a skill name.'
            )

        if errors:
            raise ValidationError(
                errors
            )

    def save(
        self,
        *args,
        **kwargs,
    ):
        if self.video_file:

            if not self.original_filename:

                self.original_filename = (
                    Path(
                        self.video_file.name
                    ).name
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
    def file_size_mb(
        self,
    ):
        if not self.file_size_bytes:
            return None

        return round(
            self.file_size_bytes
            / 1024
            / 1024,
            1,
        )

    @property
    def formatted_duration(
        self,
    ):
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
    def tag_list(
        self,
    ):
        if not self.tags:
            return []

        return [
            tag.strip()

            for tag
            in self.tags.split(',')

            if tag.strip()
        ]


# ============================================================
# VIDEO REVIEW
# ============================================================


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

    assigned_coach = (
        models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            related_name=(
                'assigned_video_reviews'
            ),
            null=True,
            blank=True,
            limit_choices_to={
                'role__in': [
                    'coach',
                    'head_coach',
                ],
            },
        )
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            'requested_video_reviews'
        ),
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
                name=(
                    'unique_video_review_per_coach'
                ),
            ),
        ]

    def __str__(
        self,
    ):
        return (
            f'{self.video.title} - '
            f'{self.get_status_display()}'
        )


# ============================================================
# VIDEO ANALYSIS
# ============================================================


class VideoAnalysis(models.Model):

    STATUS_QUEUED = 'queued'
    STATUS_PREPARING = 'preparing'
    STATUS_PROCESSING = 'processing'

    STATUS_GENERATING_RESULTS = (
        'generating_results'
    )

    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (
            STATUS_QUEUED,
            'Queued',
        ),
        (
            STATUS_PREPARING,
            'Preparing Video',
        ),
        (
            STATUS_PROCESSING,
            'Processing Frames',
        ),
        (
            STATUS_GENERATING_RESULTS,
            'Generating Results',
        ),
        (
            STATUS_COMPLETED,
            'Completed',
        ),
        (
            STATUS_FAILED,
            'Failed',
        ),
        (
            STATUS_CANCELLED,
            'Cancelled',
        ),
    ]

    REVIEW_PENDING = 'pending'
    REVIEW_APPROVED = 'approved'
    REVIEW_PARTIAL = 'partial'
    REVIEW_REJECTED = 'rejected'

    REVIEW_STATUS_CHOICES = [
        (
            REVIEW_PENDING,
            'Pending Coach Review',
        ),
        (
            REVIEW_APPROVED,
            'Approved',
        ),
        (
            REVIEW_PARTIAL,
            'Partially Correct',
        ),
        (
            REVIEW_REJECTED,
            'Rejected',
        ),
    ]

    SOURCE_MOCK = 'mock'
    SOURCE_POSE = 'pose'
    SOURCE_MULTIMODAL = 'multimodal'
    SOURCE_HYBRID = 'hybrid'

    SOURCE_CHOICES = [
        (
            SOURCE_MOCK,
            'Mock Analysis',
        ),
        (
            SOURCE_POSE,
            'Pose Analysis',
        ),
        (
            SOURCE_MULTIMODAL,
            'Multimodal Analysis',
        ),
        (
            SOURCE_HYBRID,
            'Hybrid Analysis',
        ),
    ]

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='analyses',
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            'requested_video_analyses'
        ),
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )

    progress_percentage = (
        models.PositiveSmallIntegerField(
            default=0,
            help_text=(
                'Processing progress '
                'from 0 to 100.'
            ),
        )
    )

    current_step = models.CharField(
        max_length=200,
        blank=True,
    )

    analysis_source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default=SOURCE_MOCK,
    )

    analysis_version = models.CharField(
        max_length=50,
        default='0.1.0',
    )

    requested_skill = models.CharField(
        max_length=150,
        blank=True,
    )

    detected_skill = models.CharField(
        max_length=150,
        blank=True,
    )

    skill_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    summary = models.TextField(
        blank=True,
    )

    strengths = models.JSONField(
        default=list,
        blank=True,
    )

    improvements = models.JSONField(
        default=list,
        blank=True,
    )

    measurements = models.JSONField(
        default=dict,
        blank=True,
    )

    raw_results = models.JSONField(
        default=dict,
        blank=True,
    )

    annotated_video = models.FileField(
        upload_to=(
            analysis_video_upload_path
        ),
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    processing_seconds = (
        models.DecimalField(
            max_digits=10,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )

    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default=REVIEW_PENDING,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            'reviewed_video_analyses'
        ),
        null=True,
        blank=True,
    )

    coach_review_notes = (
        models.TextField(
            blank=True,
        )
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            '-created_at',
        ]

        indexes = [
            models.Index(
                fields=[
                    'status',
                    'created_at',
                ],
                name=(
                    'analysis_status_date_idx'
                ),
            ),

            models.Index(
                fields=[
                    'video',
                    'status',
                ],
                name=(
                    'analysis_video_status_idx'
                ),
            ),

            models.Index(
                fields=[
                    'review_status',
                ],
                name='analysis_review_idx',
            ),
        ]

    def __str__(
        self,
    ):
        return (
            f'{self.video.title} - '
            f'{self.get_status_display()}'
        )

    def clean(
        self,
    ):
        errors = {}

        if (
            self.progress_percentage
            > 100
        ):
            errors[
                'progress_percentage'
            ] = (
                'Progress cannot exceed '
                '100 percent.'
            )

        if (
            self.skill_confidence
            is not None
            and (
                self.skill_confidence < 0
                or
                self.skill_confidence > 1
            )
        ):
            errors[
                'skill_confidence'
            ] = (
                'Confidence must be '
                'between 0 and 1.'
            )

        if errors:

            raise ValidationError(
                errors
            )

    def mark_started(
        self,
        step='Preparing video',
    ):
        self.status = (
            self.STATUS_PREPARING
        )

        self.progress_percentage = 5

        self.current_step = step

        self.started_at = (
            timezone.now()
        )

        self.error_message = ''

        self.save(
            update_fields=[
                'status',
                'progress_percentage',
                'current_step',
                'started_at',
                'error_message',
                'updated_at',
            ],
        )

    def update_progress(
        self,
        percentage,
        step,
        status=None,
    ):
        self.progress_percentage = max(
            0,
            min(
                int(
                    percentage
                ),
                100,
            ),
        )

        self.current_step = step

        update_fields = [
            'progress_percentage',
            'current_step',
            'updated_at',
        ]

        if status:

            self.status = status

            update_fields.append(
                'status'
            )

        self.save(
            update_fields=(
                update_fields
            ),
        )

    def mark_completed(
        self,
    ):
        self.status = (
            self.STATUS_COMPLETED
        )

        self.progress_percentage = 100

        self.current_step = (
            'Analysis complete'
        )

        self.completed_at = (
            timezone.now()
        )

        self.error_message = ''

        if self.started_at:

            elapsed = (
                self.completed_at
                - self.started_at
            ).total_seconds()

            self.processing_seconds = (
                elapsed
            )

        self.save(
            update_fields=[
                'status',
                'progress_percentage',
                'current_step',
                'completed_at',
                'processing_seconds',
                'error_message',
                'updated_at',
            ],
        )

    def mark_failed(
        self,
        message,
    ):
        self.status = (
            self.STATUS_FAILED
        )

        self.current_step = (
            'Analysis failed'
        )

        self.error_message = str(
            message
        )

        self.completed_at = (
            timezone.now()
        )

        if self.started_at:

            elapsed = (
                self.completed_at
                - self.started_at
            ).total_seconds()

            self.processing_seconds = (
                elapsed
            )

        self.save(
            update_fields=[
                'status',
                'current_step',
                'error_message',
                'completed_at',
                'processing_seconds',
                'updated_at',
            ],
        )

    @property
    def is_finished(
        self,
    ):
        return self.status in [
            self.STATUS_COMPLETED,
            self.STATUS_FAILED,
            self.STATUS_CANCELLED,
        ]

    @property
    def confidence_percentage(
        self,
    ):
        if (
            self.skill_confidence
            is None
        ):
            return None

        return round(
            float(
                self.skill_confidence
            )
            * 100,
            1,
        )


# ============================================================
# VIDEO ANALYSIS MOMENT
# ============================================================


class VideoAnalysisMoment(models.Model):

    MOMENT_START = 'start'
    MOMENT_APPROACH = 'approach'
    MOMENT_TAKEOFF = 'takeoff'

    MOMENT_HAND_SUPPORT = (
        'hand_support'
    )

    MOMENT_RELEASE = 'release'
    MOMENT_FLIGHT = 'flight'
    MOMENT_CATCH = 'catch'
    MOMENT_LANDING = 'landing'
    MOMENT_FINISH = 'finish'

    MOMENT_OBSERVATION = (
        'observation'
    )

    MOMENT_OTHER = 'other'

    MOMENT_TYPE_CHOICES = [
        (
            MOMENT_START,
            'Start',
        ),
        (
            MOMENT_APPROACH,
            'Approach',
        ),
        (
            MOMENT_TAKEOFF,
            'Takeoff',
        ),
        (
            MOMENT_HAND_SUPPORT,
            'Hand Support',
        ),
        (
            MOMENT_RELEASE,
            'Release',
        ),
        (
            MOMENT_FLIGHT,
            'Flight',
        ),
        (
            MOMENT_CATCH,
            'Catch',
        ),
        (
            MOMENT_LANDING,
            'Landing',
        ),
        (
            MOMENT_FINISH,
            'Finish',
        ),
        (
            MOMENT_OBSERVATION,
            'Observation',
        ),
        (
            MOMENT_OTHER,
            'Other',
        ),
    ]

    SEVERITY_INFO = 'info'
    SEVERITY_POSITIVE = 'positive'
    SEVERITY_WARNING = 'warning'
    SEVERITY_CRITICAL = 'critical'

    SEVERITY_CHOICES = [
        (
            SEVERITY_INFO,
            'Information',
        ),
        (
            SEVERITY_POSITIVE,
            'Positive',
        ),
        (
            SEVERITY_WARNING,
            'Needs Attention',
        ),
        (
            SEVERITY_CRITICAL,
            'Significant Concern',
        ),
    ]

    analysis = models.ForeignKey(
        VideoAnalysis,
        on_delete=models.CASCADE,
        related_name='moments',
    )

    timestamp_seconds = (
        models.DecimalField(
            max_digits=10,
            decimal_places=3,
        )
    )

    end_timestamp_seconds = (
        models.DecimalField(
            max_digits=10,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )

    moment_type = models.CharField(
        max_length=30,
        choices=MOMENT_TYPE_CHOICES,
        default=MOMENT_OBSERVATION,
    )

    label = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    measurements = models.JSONField(
        default=dict,
        blank=True,
    )

    frame_image = models.ImageField(
        upload_to=(
            analysis_frame_upload_path
        ),
        null=True,
        blank=True,
    )

    display_order = (
        models.PositiveIntegerField(
            default=0,
        )
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            'timestamp_seconds',
            'display_order',
            'id',
        ]

        indexes = [
            models.Index(
                fields=[
                    'analysis',
                    'timestamp_seconds',
                ],
                name=(
                    'analysis_moment_time_idx'
                ),
            ),

            models.Index(
                fields=[
                    'moment_type',
                ],
                name=(
                    'analysis_moment_type_idx'
                ),
            ),
        ]

    def __str__(
        self,
    ):
        return (
            f'{self.analysis.video.title} - '
            f'{self.label} at '
            f'{self.timestamp_seconds}s'
        )

    def clean(
        self,
    ):
        errors = {}

        if self.timestamp_seconds < 0:

            errors[
                'timestamp_seconds'
            ] = (
                'The timestamp cannot '
                'be negative.'
            )

        if (
            self.end_timestamp_seconds
            is not None
            and
            self.end_timestamp_seconds
            <
            self.timestamp_seconds
        ):
            errors[
                'end_timestamp_seconds'
            ] = (
                'The end timestamp must '
                'be after the start timestamp.'
            )

        if (
            self.confidence
            is not None
            and (
                self.confidence < 0
                or
                self.confidence > 1
            )
        ):
            errors[
                'confidence'
            ] = (
                'Confidence must be '
                'between 0 and 1.'
            )

        if errors:

            raise ValidationError(
                errors
            )

    @property
    def confidence_percentage(
        self,
    ):
        if self.confidence is None:
            return None

        return round(
            float(
                self.confidence
            )
            * 100,
            1,
        )


# ============================================================
# VIDEO ANALYSIS FEEDBACK
# ============================================================


class VideoAnalysisFeedback(
    models.Model
):

    RATING_CORRECT = 'correct'
    RATING_PARTIAL = 'partial'
    RATING_INCORRECT = 'incorrect'

    RATING_CHOICES = [
        (
            RATING_CORRECT,
            'Correct',
        ),
        (
            RATING_PARTIAL,
            'Partially Correct',
        ),
        (
            RATING_INCORRECT,
            'Incorrect',
        ),
    ]

    analysis = models.ForeignKey(
        VideoAnalysis,
        on_delete=models.CASCADE,
        related_name=(
            'feedback_entries'
        ),
    )

    moment = models.ForeignKey(
        VideoAnalysisMoment,
        on_delete=models.CASCADE,
        related_name=(
            'feedback_entries'
        ),
        null=True,
        blank=True,
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=(
            'video_analysis_feedback'
        ),
    )

    rating = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
    )

    comment = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            '-created_at',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'analysis',
                    'moment',
                    'coach',
                ],
                name=(
                    'unique_analysis_moment_feedback_per_coach'
                ),
            ),
        ]

    def __str__(
        self,
    ):
        return (
            f'{self.analysis.video.title} - '
            f'{self.coach.username} - '
            f'{self.get_rating_display()}'
        )


# ============================================================
# TECHNIQUE PROFILE
# ============================================================


class TechniqueProfile(
    models.Model
):

    STRICTNESS_DEVELOPMENTAL = (
        'developmental'
    )

    STRICTNESS_STANDARD = (
        'standard'
    )

    STRICTNESS_HIGH_PERFORMANCE = (
        'high_performance'
    )

    STRICTNESS_CHOICES = [
        (
            STRICTNESS_DEVELOPMENTAL,
            'Developmental',
        ),
        (
            STRICTNESS_STANDARD,
            'Standard',
        ),
        (
            STRICTNESS_HIGH_PERFORMANCE,
            'High Performance',
        ),
    ]

    skill_name = models.CharField(
        max_length=120,
        unique=True,
    )

    strictness = models.CharField(
        max_length=30,
        choices=STRICTNESS_CHOICES,
        default=STRICTNESS_STANDARD,
    )

    straight_legs = models.BooleanField(
        default=True,
    )

    body_line = models.BooleanField(
        default=True,
    )

    shoulder_position = (
        models.BooleanField(
            default=True,
        )
    )

    straight_arms = models.BooleanField(
        default=True,
    )

    landing_control = (
        models.BooleanField(
            default=False,
        )
    )

    takeoff_position = (
        models.BooleanField(
            default=False,
        )
    )

    tuck_position = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            'created_technique_profiles'
        ),
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            'updated_technique_profiles'
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            'skill_name',
        ]

    def __str__(
        self,
    ):
        return (
            f'{self.skill_name} '
            f'('
            f'{self.get_strictness_display()}'
            f')'
        )

    @property
    def active_emphases(
        self,
    ):
        emphasis_map = {
            (
                'straight_legs'
            ): (
                'Straight Legs'
            ),

            (
                'body_line'
            ): (
                'Body Line'
            ),

            (
                'shoulder_position'
            ): (
                'Shoulder Position'
            ),

            (
                'straight_arms'
            ): (
                'Straight Arms'
            ),

            (
                'landing_control'
            ): (
                'Landing Control'
            ),

            (
                'takeoff_position'
            ): (
                'Takeoff Position'
            ),

            (
                'tuck_position'
            ): (
                'Tuck Position'
            ),
        }

        return [
            label

            for field, label
            in emphasis_map.items()

            if getattr(
                self,
                field,
                False,
            )
        ]