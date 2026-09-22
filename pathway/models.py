from django.conf import settings
from django.db import models


# ============================================================
# PATHWAY LEVEL
# ============================================================


class PathwayLevel(models.Model):

    PROGRAM_HP = 'hp'
    PROGRAM_USAG_OPTIONAL = 'usag_optional_2026'
    PROGRAM_CHOICES = [
        (PROGRAM_HP, 'High Performance'),
        (PROGRAM_USAG_OPTIONAL, 'USAG Optional 2026–2030'),
    ]

    program = models.CharField(
        max_length=30,
        choices=PROGRAM_CHOICES,
        default=PROGRAM_HP,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    minimum_age = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    maximum_age = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
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
            'order',
            'name',
        ]

    def __str__(self):
        return self.name


# ============================================================
# PATHWAY EVENT
# ============================================================


class PathwayEvent(models.Model):

    EVENT_VAULT = 'vault'
    EVENT_BARS = 'bars'
    EVENT_BEAM = 'beam'
    EVENT_FLOOR = 'floor'

    EVENT_CHOICES = [
        (
            EVENT_VAULT,
            'Vault',
        ),
        (
            EVENT_BARS,
            'Uneven Bars',
        ),
        (
            EVENT_BEAM,
            'Beam',
        ),
        (
            EVENT_FLOOR,
            'Floor',
        ),
    ]

    code = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            'order',
            'name',
        ]

    def __str__(self):
        return self.name


# ============================================================
# PATHWAY REQUIREMENT
# ============================================================


class PathwayRequirement(models.Model):

    TYPE_SKILL = 'skill'
    TYPE_CR = 'cr'
    TYPE_BONUS = 'bonus'
    TYPE_DV = 'dv'
    TYPE_ROUTINE = 'routine'
    TYPE_VAULT = 'vault'
    TYPE_EQUIPMENT = 'equipment'
    TYPE_COMPETITION = 'competition'
    TYPE_OTHER = 'other'

    TYPE_CHOICES = [
        (
            TYPE_SKILL,
            'Skill',
        ),
        (
            TYPE_CR,
            'Composition Requirement',
        ),
        (
            TYPE_BONUS,
            'Bonus',
        ),
        (
            TYPE_DV,
            'Difficulty Value',
        ),
        (
            TYPE_ROUTINE,
            'Routine Requirement',
        ),
        (
            TYPE_VAULT,
            'Vault Option',
        ),
        (
            TYPE_EQUIPMENT,
            'Equipment',
        ),
        (
            TYPE_COMPETITION,
            'Competition Requirement',
        ),
        (
            TYPE_OTHER,
            'Other',
        ),
    ]

    level = models.ForeignKey(
        PathwayLevel,
        on_delete=models.CASCADE,
        related_name='requirements',
    )

    event = models.ForeignKey(
        PathwayEvent,
        on_delete=models.CASCADE,
        related_name='requirements',
    )

    requirement_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_SKILL,
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    requirement_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    bonus_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    parent_requirement = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_requirements',
    )

    is_required = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    notes = models.TextField(
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
            'level__order',
            'event__order',
            'display_order',
            'requirement_number',
            'title',
        ]

    def __str__(self):
        return (
            f'{self.level} - '
            f'{self.event} - '
            f'{self.title}'
        )


# ============================================================
# ATHLETE PATHWAY
# ============================================================


class AthletePathway(models.Model):

    STATUS_DEVELOPING = 'developing'
    STATUS_ON_TRACK = 'on_track'
    STATUS_READY = 'ready'
    STATUS_HOLD = 'hold'

    STATUS_CHOICES = [
        (
            STATUS_DEVELOPING,
            'Developing',
        ),
        (
            STATUS_ON_TRACK,
            'On Track',
        ),
        (
            STATUS_READY,
            'Ready for Next Level',
        ),
        (
            STATUS_HOLD,
            'Hold',
        ),
    ]

    athlete = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hp_pathway',
        limit_choices_to={
            'role': 'athlete',
        },
    )

    current_level = models.ForeignKey(
        PathwayLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_athletes',
    )

    target_level = models.ForeignKey(
        PathwayLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='target_athletes',
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DEVELOPING,
    )

    target_date = models.DateField(
        null=True,
        blank=True,
    )

    head_coach_notes = models.TextField(
        blank=True,
    )

    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_hp_pathways',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f'{self.athlete} - '
            f'{self.current_level or "No Level"}'
        )

    @property
    def has_usag_optional_level(self):
        return any(
            level and level.program == PathwayLevel.PROGRAM_USAG_OPTIONAL
            for level in (self.current_level, self.target_level)
        )


# ============================================================
# ATHLETE PATHWAY REQUIREMENT
# ============================================================


class AthletePathwayRequirement(models.Model):
    STATUS_NOT_STARTED = 'not_started'
    STATUS_DEVELOPING = 'developing'
    STATUS_ACHIEVED = 'achieved'
    STATUS_COMPETITION_READY = 'competition_ready'

    STATUS_CHOICES = [
        (
            STATUS_NOT_STARTED,
            'Not Started',
        ),
        (
            STATUS_DEVELOPING,
            'Developing',
        ),
        (
            STATUS_ACHIEVED,
            'Achieved',
        ),
        (
            STATUS_COMPETITION_READY,
            'Competition Ready',
        ),


    ]

    athlete_pathway = models.ForeignKey(
        AthletePathway,
        on_delete=models.CASCADE,
        related_name='athlete_requirements',
    )

    requirement = models.ForeignKey(
        PathwayRequirement,
        on_delete=models.CASCADE,
        related_name='athlete_statuses',
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
    )

    coach_note = models.TextField(
        blank=True,
    )

    target_date = models.DateField(
        null=True,
        blank=True,
    )

    custom_title = models.CharField(
        max_length=200,
        blank=True,
    )

    is_hidden_from_parent = models.BooleanField(
        default=False,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_pathway_requirements',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'athlete_pathway',
                    'requirement',
                ],
                name='unique_athlete_pathway_requirement',
            ),
        ]

        ordering = [
            'requirement__event__order',
            'requirement__display_order',
        ]

    def __str__(self):
        return (
            f'{self.athlete_pathway.athlete} - '
            f'{self.requirement.title}'
        )

# ============================================================
# ATHLETE ROUTINE
# ============================================================


class AthleteRoutine(models.Model):

    EVENT_VAULT = 'vault'
    EVENT_BARS = 'bars'
    EVENT_BEAM = 'beam'
    EVENT_FLOOR = 'floor'

    EVENT_CHOICES = [
        (
            EVENT_VAULT,
            'Vault',
        ),
        (
            EVENT_BARS,
            'Uneven Bars',
        ),
        (
            EVENT_BEAM,
            'Beam',
        ),
        (
            EVENT_FLOOR,
            'Floor',
        ),
    ]


    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hp_routines',
        limit_choices_to={
            'role': 'athlete',
        },
    )


    pathway_level = models.ForeignKey(
        PathwayLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='athlete_routines',
    )


    event = models.CharField(
        max_length=20,
        choices=EVENT_CHOICES,
    )


    name = models.CharField(
        max_length=120,
        default='Competition Routine',
    )


    is_current = models.BooleanField(
        default=True,
    )


    notes = models.TextField(
        blank=True,
    )


    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_hp_routines',
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
            'event',
            '-is_current',
            'name',
        ]


    def __str__(self):
        return (
            f'{self.athlete} - '
            f'{self.get_event_display()} - '
            f'{self.name}'
        )

# ============================================================
# ATHLETE ROUTINE ELEMENT
# ============================================================


class AthleteRoutineElement(models.Model):

    DIFFICULTY_A = 'A'
    DIFFICULTY_B = 'B'
    DIFFICULTY_C = 'C'
    DIFFICULTY_D = 'D'
    DIFFICULTY_E_PLUS = 'E+'

    DIFFICULTY_CHOICES = [
        (
            DIFFICULTY_A,
            'A',
        ),
        (
            DIFFICULTY_B,
            'B',
        ),
        (
            DIFFICULTY_C,
            'C',
        ),
        (
            DIFFICULTY_D,
            'D',
        ),
        (
            DIFFICULTY_E_PLUS,
            'E+',
        ),
    ]


    ELEMENT_ACRO = 'acro'
    ELEMENT_DANCE = 'dance'
    ELEMENT_OTHER = 'other'

    ELEMENT_TYPE_CHOICES = [
        (
            ELEMENT_ACRO,
            'Acro',
        ),
        (
            ELEMENT_DANCE,
            'Dance',
        ),
        (
            ELEMENT_OTHER,
            'Other',
        ),
    ]


    routine = models.ForeignKey(
        AthleteRoutine,
        on_delete=models.CASCADE,
        related_name='elements',
    )


    skill_name = models.CharField(
        max_length=150,
    )


    difficulty = models.CharField(
        max_length=5,
        choices=DIFFICULTY_CHOICES,
    )


    difficulty_value = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
    )


    element_type = models.CharField(
        max_length=20,
        choices=ELEMENT_TYPE_CHOICES,
        default=ELEMENT_OTHER,
    )


    order = models.PositiveIntegerField(
        default=1,
    )


    is_dismount = models.BooleanField(
        default=False,
    )


    notes = models.CharField(
        max_length=250,
        blank=True,
    )


    class Meta:
        ordering = [
            'order',
            'id',
        ]

    vault_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )


    def __str__(self):
        return (
            f'{self.routine} - '
            f'{self.skill_name}'
        )

# ============================================================
# ATHLETE ROUTINE REQUIREMENT
# ============================================================


class AthleteRoutineRequirement(models.Model):

    routine = models.ForeignKey(
        AthleteRoutine,
        on_delete=models.CASCADE,
        related_name='routine_requirements',
    )


    requirement = models.ForeignKey(
        PathwayRequirement,
        on_delete=models.CASCADE,
        related_name='routine_uses',
    )


    is_met = models.BooleanField(
        default=False,
    )


    notes = models.CharField(
        max_length=250,
        blank=True,
    )


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'routine',
                    'requirement',
                ],
                name='unique_routine_requirement',
            ),
        ]


    def __str__(self):
        return (
            f'{self.routine} - '
            f'{self.requirement.title}'
        )
