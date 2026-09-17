from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TestingExercise(models.Model):
    UNIT_CHOICES = [
        ('points', 'Points'),
        ('reps', 'Repetitions'),
        ('seconds', 'Seconds'),
        ('minutes', 'Minutes'),
        ('distance', 'Distance'),
        ('level', 'Level'),
        ('text', 'Text Result'),
        ('pass_fail', 'Pass / Fail'),
    ]

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='points',
    )

    higher_is_better = models.BooleanField(
        default=True,
        help_text=(
            'Select this when a higher result is better. '
            'Turn it off when a lower time or score is better.'
        ),
    )

    guidelines = models.TextField(
        blank=True,
        help_text=(
            'Explain how this exercise is performed and scored.'
        ),
    )

    active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_testing_exercises',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            'display_order',
            'name',
        ]

    def __str__(self):
        return self.name


class TestingSession(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_READY = 'ready'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (
            STATUS_DRAFT,
            'Draft',
        ),
        (
            STATUS_READY,
            'Ready',
        ),
        (
            STATUS_IN_PROGRESS,
            'In Progress',
        ),
        (
            STATUS_COMPLETED,
            'Completed',
        ),
    ]

    title = models.CharField(
        max_length=150,
    )

    testing_date = models.DateField()

    week_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            'Optional weekly testing number, such as Week 3.'
        ),
    )

    training_group = models.ForeignKey(
        'gyms.TrainingGroup',
        on_delete=models.SET_NULL,
        related_name='testing_sessions',
        null=True,
        blank=True,
        help_text=(
            'The training group completing this testing session.'
        ),
    )

    practice_plan = models.ForeignKey(
        'practice_planner.PracticePlan',
        on_delete=models.SET_NULL,
        related_name='testing_sessions',
        null=True,
        blank=True,
        help_text=(
            'Optional practice plan where this testing session '
            'will be completed.'
        ),
    )

    exercises = models.ManyToManyField(
        TestingExercise,
        related_name='testing_sessions',
    )

    athletes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='performance_testing_sessions',
        blank=True,
        limit_choices_to={
            'role': 'athlete',
        },
    )

    notes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_testing_sessions',
    )

    allow_athlete_entry = models.BooleanField(
        default=False,
    )

    published_to_athletes = models.BooleanField(
        default=False,
    )

    published_to_parents = models.BooleanField(
        default=False,
    )

    show_rankings_to_athletes = models.BooleanField(
        default=True,
    )

    show_rankings_to_parents = models.BooleanField(
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
            '-testing_date',
            '-created_at',
        ]

    def __str__(self):
        details = [
            self.title,
            str(self.testing_date),
        ]

        if self.week_number:
            details.insert(
                1,
                f'Week {self.week_number}',
            )

        return ' - '.join(details)

    def clean(self):
        errors = {}

        if (
            self.practice_plan_id
            and self.testing_date
            != self.practice_plan.practice_date
        ):
            errors['testing_date'] = (
                'The testing date must match the linked '
                'practice date.'
            )

        if errors:
            raise ValidationError(errors)

    def copy_group_athletes(self):
        """
        Add all active athletes from the selected training group.
        """

        if not self.training_group_id:
            return

        athletes = (
            self.training_group
            .athlete_assignments
            .filter(
                is_active=True,
                athlete__is_active=True,
            )
            .select_related('athlete')
        )

        self.athletes.add(
            *(
                assignment.athlete
                for assignment in athletes
            )
        )

    @property
    def athlete_count(self):
        return self.athletes.count()

    @property
    def completed_result_count(self):
        return self.athlete_results.filter(
            status='verified',
        ).count()

    @property
    def missing_result_count(self):
        return max(
            self.athlete_count
            - self.completed_result_count,
            0,
        )


class AthleteTestingResult(models.Model):
    STATUS_CHOICES = [
        (
            'draft',
            'Draft',
        ),
        (
            'pending',
            'Pending Coach Verification',
        ),
        (
            'verified',
            'Verified',
        ),
    ]

    session = models.ForeignKey(
        TestingSession,
        on_delete=models.CASCADE,
        related_name='athlete_results',
    )

    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='performance_testing_results',
    )

    total_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    rank = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
    )

    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_performance_testing_results',
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_performance_testing_results',
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
            'rank',
            '-total_score',
            'athlete__username',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'session',
                    'athlete',
                ],
                name='unique_athlete_testing_result_per_session',
            ),
        ]

    def __str__(self):
        return (
            f'{self.athlete.username} - '
            f'{self.session.title} - '
            f'{self.total_score}'
        )

    def calculate_total_score(self):
        total = self.exercise_results.filter(
            not_completed=False,
        ).aggregate(
            total=models.Sum('score'),
        )['total']

        self.total_score = (
            total
            or Decimal('0.00')
        )

        self.save(
            update_fields=[
                'total_score',
            ],
        )

        return self.total_score

    def get_previous_result(self):
        return (
            AthleteTestingResult.objects
            .filter(
                athlete=self.athlete,
                session__testing_date__lt=(
                    self.session.testing_date
                ),
                status='verified',
            )
            .exclude(
                id=self.id,
            )
            .select_related(
                'session',
            )
            .order_by(
                '-session__testing_date',
            )
            .first()
        )

    @property
    def previous_score(self):
        previous = self.get_previous_result()

        if previous:
            return previous.total_score

        return None

    @property
    def score_change(self):
        previous = self.get_previous_result()

        if not previous:
            return None

        return (
            self.total_score
            - previous.total_score
        )


class TestingExerciseResult(models.Model):
    athlete_result = models.ForeignKey(
        AthleteTestingResult,
        on_delete=models.CASCADE,
        related_name='exercise_results',
    )

    exercise = models.ForeignKey(
        TestingExercise,
        on_delete=models.CASCADE,
        related_name='athlete_exercise_results',
    )

    raw_result = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            'Examples: 24, 7.17 seconds, 5 presses, '
            'or white line.'
        ),
    )

    numeric_result = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=(
            'Optional numeric value used later for '
            'automatic scoring.'
        ),
    )

    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    not_completed = models.BooleanField(
        default=False,
    )

    notes = models.CharField(
        max_length=255,
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
            'exercise__display_order',
            'exercise__name',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'athlete_result',
                    'exercise',
                ],
                name='unique_exercise_result_per_athlete_result',
            ),
        ]

    def __str__(self):
        return (
            f'{self.athlete_result.athlete.username} - '
            f'{self.exercise.name}'
        )


class TestingScoringRule(models.Model):
    COMPARISON_CHOICES = [
        (
            'gte',
            'Greater than or equal to',
        ),
        (
            'lte',
            'Less than or equal to',
        ),
        (
            'between',
            'Between',
        ),
        (
            'exact',
            'Exactly',
        ),
    ]

    exercise = models.ForeignKey(
        TestingExercise,
        on_delete=models.CASCADE,
        related_name='scoring_rules',
    )

    label = models.CharField(
        max_length=150,
        help_text=(
            'Example: 10 L leg lifts'
        ),
    )

    comparison = models.CharField(
        max_length=20,
        choices=COMPARISON_CHOICES,
        default='gte',
    )

    minimum_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )

    maximum_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )

    points = models.DecimalField(
        max_digits=7,
        decimal_places=2,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            'exercise__display_order',
            'display_order',
            'points',
        ]

    def __str__(self):
        return (
            f'{self.exercise.name}: '
            f'{self.label} = '
            f'{self.points} points'
        )
