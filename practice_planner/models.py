from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TrainingGroup(models.Model):
    """
    A recurring group of athletes who normally train together.

    Examples:
    - WAG A
    - HP Novice
    - Aspire 1
    """

    name = models.CharField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    coaches = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='practice_training_groups',
        blank=True,
        limit_choices_to={
            'role__in': [
                'coach',
                'head_coach',
            ],
        },
    )

    athletes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='practice_groups',
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            'name',
        ]

    def __str__(self):
        return self.name


class PracticePlan(models.Model):
    """
    The main record for one planned practice.
    """

    STATUS_DRAFT = 'draft'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (
            STATUS_DRAFT,
            'Draft',
        ),
        (
            STATUS_SCHEDULED,
            'Scheduled',
        ),
        (
            STATUS_IN_PROGRESS,
            'In Progress',
        ),
        (
            STATUS_COMPLETED,
            'Completed',
        ),
        (
            STATUS_CANCELLED,
            'Cancelled',
        ),
    ]

    INTENSITY_LOW = 'low'
    INTENSITY_MODERATE = 'moderate'
    INTENSITY_HIGH = 'high'
    INTENSITY_COMPETITION = 'competition'

    INTENSITY_CHOICES = [
        (
            INTENSITY_LOW,
            'Low',
        ),
        (
            INTENSITY_MODERATE,
            'Moderate',
        ),
        (
            INTENSITY_HIGH,
            'High',
        ),
        (
            INTENSITY_COMPETITION,
            'Competition Simulation',
        ),
    ]

    title = models.CharField(
        max_length=180,
    )

    practice_date = models.DateField(
        default=timezone.localdate,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    training_group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.PROTECT,
        related_name='practice_plans',
    )

    lead_coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='led_practice_plans',
        limit_choices_to={
            'role__in': [
                'coach',
                'head_coach',
            ],
        },
    )

    assistant_coaches = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assisted_practice_plans',
        blank=True,
        limit_choices_to={
            'role__in': [
                'coach',
                'head_coach',
            ],
        },
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    planned_intensity = models.CharField(
        max_length=20,
        choices=INTENSITY_CHOICES,
        default=INTENSITY_MODERATE,
    )

    primary_focus = models.CharField(
        max_length=200,
        blank=True,
    )

    coach_objectives = models.TextField(
        blank=True,
    )

    general_notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_practice_plans',
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
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
            '-practice_date',
            '-start_time',
        ]

    def __str__(self):
        return (
            f'{self.title} - '
            f'{self.training_group.name} - '
            f'{self.practice_date}'
        )

    def clean(self):
        errors = {}

        if (
            self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            errors['end_time'] = (
                'The practice end time must be after '
                'the start time.'
            )

        if (
            self.lead_coach_id
            and self.lead_coach.role not in [
                'coach',
                'head_coach',
            ]
        ):
            errors['lead_coach'] = (
                'The lead coach must have a coach or '
                'head coach role.'
            )

        if errors:
            raise ValidationError(errors)

    @property
    def duration_minutes(self):
        if not self.start_time or not self.end_time:
            return 0

        start_datetime = timezone.datetime.combine(
            self.practice_date,
            self.start_time,
        )

        end_datetime = timezone.datetime.combine(
            self.practice_date,
            self.end_time,
        )

        duration = end_datetime - start_datetime

        return int(
            duration.total_seconds() / 60
        )


class PracticeRotation(models.Model):
    """
    A timed portion of a practice.

    Examples:
    - Bars
    - Beam
    - Floor
    - Strength
    - Weekly Testing
    """

    EVENT_VAULT = 'vault'
    EVENT_BARS = 'bars'
    EVENT_BEAM = 'beam'
    EVENT_FLOOR = 'floor'
    EVENT_TRAMPOLINE = 'trampoline'
    EVENT_STRENGTH = 'strength'
    EVENT_FLEXIBILITY = 'flexibility'
    EVENT_CONDITIONING = 'conditioning'
    EVENT_DANCE = 'dance'
    EVENT_WARMUP = 'warmup'
    EVENT_TESTING = 'testing'
    EVENT_RECOVERY = 'recovery'
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
            EVENT_FLEXIBILITY,
            'Flexibility',
        ),
        (
            EVENT_CONDITIONING,
            'Conditioning',
        ),
        (
            EVENT_DANCE,
            'Dance',
        ),
        (
            EVENT_WARMUP,
            'Warm-up',
        ),
        (
            EVENT_TESTING,
            'Testing',
        ),
        (
            EVENT_RECOVERY,
            'Recovery',
        ),
        (
            EVENT_OTHER,
            'Other',
        ),
    ]

    practice_plan = models.ForeignKey(
        PracticePlan,
        on_delete=models.CASCADE,
        related_name='rotations',
    )

    title = models.CharField(
        max_length=150,
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
    )

    duration_minutes = models.PositiveIntegerField(
        default=30,
    )

    location = models.CharField(
        max_length=150,
        blank=True,
    )

    assigned_coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_practice_rotations',
        null=True,
        blank=True,
        limit_choices_to={
            'role__in': [
                'coach',
                'head_coach',
            ],
        },
    )

    objective = models.CharField(
        max_length=250,
        blank=True,
    )

    coach_notes = models.TextField(
        blank=True,
    )

    is_testing_rotation = models.BooleanField(
        default=False,
    )

    testing_session = models.ForeignKey(
        'performance_testing.TestingSession',
        on_delete=models.SET_NULL,
        related_name='practice_rotations',
        null=True,
        blank=True,
        help_text=(
            'Select the existing Performance Testing session '
            'used during this rotation.'
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
            'practice_plan',
            'order',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'practice_plan',
                    'order',
                ],
                name='unique_rotation_order_per_practice',
            ),
        ]

    def __str__(self):
        return (
            f'{self.practice_plan.title} - '
            f'{self.order}. {self.title}'
        )

    def clean(self):
        errors = {}

        if self.duration_minutes <= 0:
            errors['duration_minutes'] = (
                'Rotation duration must be greater than zero.'
            )

        if self.event == self.EVENT_TESTING:
            self.is_testing_rotation = True

            if not self.testing_session_id:
                errors['testing_session'] = (
                    'Choose a Performance Testing session for '
                    'this testing rotation.'
                )

        else:
            self.is_testing_rotation = False

            if self.testing_session_id:
                errors['testing_session'] = (
                    'A Performance Testing session can only be '
                    'attached to a testing rotation.'
                )

        if (
            self.testing_session_id
            and self.practice_plan_id
            and self.testing_session.practice_plan_id
            and self.testing_session.practice_plan_id
            != self.practice_plan_id
        ):
            errors['testing_session'] = (
                'This testing session is already connected to '
                'a different practice plan.'
            )

        if (
            self.testing_session_id
            and self.practice_plan_id
            and self.testing_session.training_group_id
            and self.testing_session.training_group_id
            != self.practice_plan.training_group_id
        ):
            errors['testing_session'] = (
                'The testing session training group must match '
                'the practice training group.'
            )

        if errors:
            raise ValidationError(errors)


class PracticeStation(models.Model):
    """
    A drill, skill, exercise, or activity inside a rotation.
    """

    STATION_DRILL = 'drill'
    STATION_SKILL = 'skill'
    STATION_EXERCISE = 'exercise'
    STATION_TEST = 'test'
    STATION_ROUTINE = 'routine'
    STATION_CONDITIONING = 'conditioning'
    STATION_RECOVERY = 'recovery'
    STATION_OTHER = 'other'

    STATION_TYPE_CHOICES = [
        (
            STATION_DRILL,
            'Drill',
        ),
        (
            STATION_SKILL,
            'Skill',
        ),
        (
            STATION_EXERCISE,
            'Exercise',
        ),
        (
            STATION_TEST,
            'Testing Exercise',
        ),
        (
            STATION_ROUTINE,
            'Routine',
        ),
        (
            STATION_CONDITIONING,
            'Conditioning',
        ),
        (
            STATION_RECOVERY,
            'Recovery',
        ),
        (
            STATION_OTHER,
            'Other',
        ),
    ]

    rotation = models.ForeignKey(
        PracticeRotation,
        on_delete=models.CASCADE,
        related_name='stations',
    )

    title = models.CharField(
        max_length=180,
    )

    station_type = models.CharField(
        max_length=30,
        choices=STATION_TYPE_CHOICES,
        default=STATION_DRILL,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    sets = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    repetitions = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    target_attempts = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    instructions = models.TextField(
        blank=True,
    )

    coaching_cues = models.TextField(
        blank=True,
    )

    equipment = models.CharField(
        max_length=250,
        blank=True,
    )

    success_criteria = models.TextField(
        blank=True,
    )

    reference_video_url = models.URLField(
        blank=True,
    )

    is_optional = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            'rotation',
            'order',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'rotation',
                    'order',
                ],
                name='unique_station_order_per_rotation',
            ),
        ]

    def __str__(self):
        return (
            f'{self.rotation.title} - '
            f'{self.order}. {self.title}'
        )

    def clean(self):
        errors = {}

        if (
            self.duration_minutes is not None
            and self.duration_minutes <= 0
        ):
            errors['duration_minutes'] = (
                'Station duration must be greater than zero.'
            )

        if errors:
            raise ValidationError(errors)


class PracticeAthleteAssignment(models.Model):
    """
    Controls whether an athlete participates in a practice and whether
    their workload differs from the rest of the training group.
    """

    WORKLOAD_FULL = 'full'
    WORKLOAD_MODIFIED = 'modified'
    WORKLOAD_RECOVERY = 'recovery'
    WORKLOAD_OBSERVE = 'observe'
    WORKLOAD_EXCUSED = 'excused'

    WORKLOAD_CHOICES = [
        (
            WORKLOAD_FULL,
            'Full Training',
        ),
        (
            WORKLOAD_MODIFIED,
            'Modified Training',
        ),
        (
            WORKLOAD_RECOVERY,
            'Recovery Program',
        ),
        (
            WORKLOAD_OBSERVE,
            'Observe Only',
        ),
        (
            WORKLOAD_EXCUSED,
            'Excused',
        ),
    ]

    practice_plan = models.ForeignKey(
        PracticePlan,
        on_delete=models.CASCADE,
        related_name='athlete_assignments',
    )

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='practice_assignments',
        limit_choices_to={
            'role': 'athlete',
        },
    )

    workload = models.CharField(
        max_length=20,
        choices=WORKLOAD_CHOICES,
        default=WORKLOAD_FULL,
    )

    is_expected = models.BooleanField(
        default=True,
    )

    restrictions = models.TextField(
        blank=True,
    )

    individual_focus = models.TextField(
        blank=True,
    )

    coach_notes = models.TextField(
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
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'practice_plan',
                    'athlete',
                ],
                name='unique_athlete_assignment_per_practice',
            ),
        ]

    def __str__(self):
        athlete_name = self.athlete.get_full_name().strip()

        if not athlete_name:
            athlete_name = self.athlete.username

        return (
            f'{athlete_name} - '
            f'{self.practice_plan.title}'
        )

    def clean(self):
        if (
            self.athlete_id
            and self.athlete.role != 'athlete'
        ):
            raise ValidationError({
                'athlete': (
                    'Only users with the athlete role can be '
                    'assigned to practices.'
                ),
            })

class PracticeTemplate(models.Model):
    """
    A reusable practice structure that coaches can copy into
    a new PracticePlan.
    """

    CATEGORY_GENERAL = 'general'
    CATEGORY_EVENT_FOCUS = 'event_focus'
    CATEGORY_COMPETITION = 'competition'
    CATEGORY_RECOVERY = 'recovery'
    CATEGORY_CONDITIONING = 'conditioning'
    CATEGORY_TESTING = 'testing'
    CATEGORY_CAMP = 'camp'
    CATEGORY_OTHER = 'other'

    CATEGORY_CHOICES = [
        (
            CATEGORY_GENERAL,
            'General Practice',
        ),
        (
            CATEGORY_EVENT_FOCUS,
            'Event Focus',
        ),
        (
            CATEGORY_COMPETITION,
            'Competition Preparation',
        ),
        (
            CATEGORY_RECOVERY,
            'Recovery Practice',
        ),
        (
            CATEGORY_CONDITIONING,
            'Conditioning',
        ),
        (
            CATEGORY_TESTING,
            'Testing',
        ),
        (
            CATEGORY_CAMP,
            'Camp',
        ),
        (
            CATEGORY_OTHER,
            'Other',
        ),
    ]

    name = models.CharField(
        max_length=180,
    )

    description = models.TextField(
        blank=True,
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
    )

    level = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            'Examples: Aspire 1, HP Novice, Level 7.'
        ),
    )

    season_phase = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            'Examples: Preseason, Competition Season, Recovery.'
        ),
    )

    planned_intensity = models.CharField(
        max_length=20,
        choices=PracticePlan.INTENSITY_CHOICES,
        default=PracticePlan.INTENSITY_MODERATE,
    )

    primary_focus = models.CharField(
        max_length=200,
        blank=True,
    )

    coach_objectives = models.TextField(
        blank=True,
    )

    general_notes = models.TextField(
        blank=True,
    )

    default_duration_minutes = models.PositiveIntegerField(
        default=180,
        help_text=(
            'The normal total duration of practices created '
            'from this template.'
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_shared = models.BooleanField(
        default=False,
        help_text=(
            'Shared templates can be viewed and used by '
            'other coaches.'
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_practice_templates',
    )

    source_practice = models.ForeignKey(
        PracticePlan,
        on_delete=models.SET_NULL,
        related_name='saved_templates',
        null=True,
        blank=True,
        help_text=(
            'The original practice used to create this template.'
        ),
    )

    times_used = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            '-updated_at',
            'name',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'created_by',
                    'name',
                ],
                name='unique_practice_template_name_per_coach',
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def total_rotation_minutes(self):
        return sum(
            rotation.duration_minutes
            for rotation in self.rotations.all()
        )

    @property
    def rotation_count(self):
        return self.rotations.count()


class PracticeTemplateRotation(models.Model):
    """
    A reusable rotation stored inside a PracticeTemplate.
    """

    template = models.ForeignKey(
        PracticeTemplate,
        on_delete=models.CASCADE,
        related_name='rotations',
    )

    title = models.CharField(
        max_length=150,
    )

    event = models.CharField(
        max_length=30,
        choices=PracticeRotation.EVENT_CHOICES,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    duration_minutes = models.PositiveIntegerField(
        default=30,
    )

    location = models.CharField(
        max_length=150,
        blank=True,
    )

    objective = models.CharField(
        max_length=250,
        blank=True,
    )

    coach_notes = models.TextField(
        blank=True,
    )

    is_optional = models.BooleanField(
        default=False,
        help_text=(
            'Optional rotations can be skipped when creating '
            'a shorter practice.'
        ),
    )

    include_testing = models.BooleanField(
        default=False,
        help_text=(
            'Marks this rotation as a testing block. '
            'A testing session will be selected when the '
            'new practice is created.'
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
            'template',
            'order',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'template',
                    'order',
                ],
                name='unique_rotation_order_per_practice_template',
            ),
        ]

    def __str__(self):
        return (
            f'{self.template.name} - '
            f'{self.order}. {self.title}'
        )


class PracticeTemplateStation(models.Model):
    """
    A reusable station stored inside a template rotation.
    """

    template_rotation = models.ForeignKey(
        PracticeTemplateRotation,
        on_delete=models.CASCADE,
        related_name='stations',
    )

    title = models.CharField(
        max_length=180,
    )

    station_type = models.CharField(
        max_length=30,
        choices=PracticeStation.STATION_TYPE_CHOICES,
        default=PracticeStation.STATION_DRILL,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    sets = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    repetitions = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    target_attempts = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    instructions = models.TextField(
        blank=True,
    )

    coaching_cues = models.TextField(
        blank=True,
    )

    equipment = models.CharField(
        max_length=250,
        blank=True,
    )

    success_criteria = models.TextField(
        blank=True,
    )

    reference_video_url = models.URLField(
        blank=True,
    )

    is_optional = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            'template_rotation',
            'order',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'template_rotation',
                    'order',
                ],
                name='unique_station_order_per_template_rotation',
            ),
        ]

    def __str__(self):
        return (
            f'{self.template_rotation.title} - '
            f'{self.order}. {self.title}'
        )