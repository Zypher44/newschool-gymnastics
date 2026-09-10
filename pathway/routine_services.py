from decimal import Decimal

from .models import (
    AthleteRoutineRequirement,
    PathwayRequirement,
)


DIFFICULTY_VALUES = {
    'A': Decimal('0.10'),
    'B': Decimal('0.20'),
    'C': Decimal('0.30'),
    'D': Decimal('0.40'),
    'E': Decimal('0.50'),
    'F': Decimal('0.60'),
    'G': Decimal('0.70'),
}


def update_element_difficulty_value(
    element,
):
    element.difficulty_value = (
        DIFFICULTY_VALUES.get(
            element.difficulty,
            Decimal('0.00'),
        )
    )

    element.save(
        update_fields=[
            'difficulty_value',
        ]
    )

from .models import (
    AthletePathwayRequirement,
    AthleteRoutineRequirement,
    PathwayRequirement,
)


def sync_routine_requirements(
    routine,
):
    """
    Attach the official pathway requirements
    for the routine's selected level and event.

    If the athlete has already been marked
    Competition Ready for a requirement in
    their HP skill tree, pre-check it for the
    routine the first time it is added.
    """

    if (
        not routine.pathway_level_id
        or not routine.event
    ):
        return


    requirements = (
        PathwayRequirement.objects
        .filter(
            level=routine.pathway_level,
            event__code=routine.event,
            is_active=True,
        )
        .order_by(
            'display_order',
            'requirement_number',
        )
    )


    athlete_pathway_statuses = {
        item.requirement_id: item.status
        for item
        in (
            AthletePathwayRequirement.objects
            .filter(
                athlete_pathway__athlete=(
                    routine.athlete
                ),
                requirement__in=(
                    requirements
                ),
            )
        )
    }


    for requirement in requirements:

        existing = (
            AthleteRoutineRequirement.objects
            .filter(
                routine=routine,
                requirement=requirement,
            )
            .first()
        )


        if existing:
            continue


        athlete_status = (
            athlete_pathway_statuses.get(
                requirement.id
            )
        )


        is_competition_ready = (
            athlete_status
            ==
            AthletePathwayRequirement
            .STATUS_COMPETITION_READY
        )


        AthleteRoutineRequirement.objects.create(
            routine=routine,
            requirement=requirement,
            is_met=is_competition_ready,
        )


def calculate_routine_d_score(
    routine,
):
    """
    Projected D score:
    element DV
    + met CR values
    + met bonuses
    """

    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    element_values = [
        element.difficulty_value
        or Decimal('0.00')
        for element
        in elements
    ]


    #
    # Bars counts the 7 highest elements,
    # including the dismount.
    #
    highest_values = sorted(
        element_values,
        reverse=True,
    )[:7]


    element_dv = sum(
        highest_values,
        Decimal('0.00'),
    )


    routine_requirements = (
        routine.routine_requirements
        .select_related(
            'requirement',
        )
        .filter(
            is_met=True,
        )
    )


    cr_total = Decimal('0.00')

    bonus_total = Decimal('0.00')


    for routine_requirement in (
        routine_requirements
    ):

        requirement = (
            routine_requirement.requirement
        )


        if (
            requirement.requirement_type
            ==
            PathwayRequirement.TYPE_BONUS
        ):

            bonus_total += (
                requirement.bonus_value
                or Decimal('0.00')
            )

        elif requirement.is_required:

            cr_total += (
                requirement.value
                or Decimal('0.00')
            )


    projected_d_score = (
        element_dv
        +
        cr_total
        +
        bonus_total
    )


    return {
        'element_dv': element_dv,
        'cr_total': cr_total,
        'bonus_total': bonus_total,
        'projected_d_score': (
            projected_d_score
        ),
    }

from decimal import Decimal


def calculate_beam_d_score(
    routine,
):
    """
    Projected Beam D score.

    Counts:
    - 7 highest elements
    - CR values
    - applicable bonuses

    Also reports Beam composition:
    - minimum 3 acro
    - minimum 3 dance
    - 1 additional optional element
    """

    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    # ========================================================
    # ELEMENT DV
    # ========================================================

    element_values = [
        element.difficulty_value
        or Decimal('0.00')
        for element
        in elements
    ]


    highest_values = sorted(
        element_values,
        reverse=True,
    )[:7]


    element_dv = sum(
        highest_values,
        Decimal('0.00'),
    )


    # ========================================================
    # COMPOSITION COUNTS
    # ========================================================

    acro_count = (
        elements
        .filter(
            element_type='acro',
        )
        .count()
    )


    dance_count = (
        elements
        .filter(
            element_type='dance',
        )
        .count()
    )


    total_element_count = (
        elements.count()
    )


    acro_requirement_met = (
        acro_count >= 3
    )

    dance_requirement_met = (
        dance_count >= 3
    )

    optional_requirement_met = (
        total_element_count >= 7
    )


    # ========================================================
    # CR + BONUS
    # ========================================================

    routine_requirements = (
        routine.routine_requirements
        .select_related(
            'requirement',
        )
        .filter(
            is_met=True,
        )
    )


    cr_total = Decimal('0.00')

    bonus_total = Decimal('0.00')


    for routine_requirement in (
        routine_requirements
    ):

        requirement = (
            routine_requirement.requirement
        )


        if (
            requirement.requirement_type
            ==
            PathwayRequirement.TYPE_BONUS
        ):

            bonus_total += (
                requirement.bonus_value
                or Decimal('0.00')
            )


        elif requirement.is_required:

            cr_total += (
                requirement.value
                or Decimal('0.00')
            )


    projected_d_score = (
        element_dv
        +
        cr_total
        +
        bonus_total
    )


    return {

        'element_dv': (
            element_dv
        ),

        'cr_total': (
            cr_total
        ),

        'bonus_total': (
            bonus_total
        ),

        'projected_d_score': (
            projected_d_score
        ),

        'acro_count': (
            acro_count
        ),

        'dance_count': (
            dance_count
        ),

        'total_element_count': (
            total_element_count
        ),

        'acro_requirement_met': (
            acro_requirement_met
        ),

        'dance_requirement_met': (
            dance_requirement_met
        ),

        'optional_requirement_met': (
            optional_requirement_met
        ),
    }


from decimal import Decimal


def calculate_floor_d_score(
    routine,
):
    """
    Projected Floor D score.

    Counts:
    - 7 highest elements
    - CR values
    - applicable bonuses

    Also reports Floor composition:
    - minimum 3 acro
    - minimum 3 dance
    - 1 additional optional element
    """

    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    element_values = [
        element.difficulty_value
        or Decimal('0.00')
        for element
        in elements
    ]


    highest_values = sorted(
        element_values,
        reverse=True,
    )[:7]


    element_dv = sum(
        highest_values,
        Decimal('0.00'),
    )


    acro_count = (
        elements
        .filter(
            element_type='acro',
        )
        .count()
    )


    dance_count = (
        elements
        .filter(
            element_type='dance',
        )
        .count()
    )


    total_element_count = (
        elements.count()
    )


    acro_requirement_met = (
        acro_count >= 3
    )

    dance_requirement_met = (
        dance_count >= 3
    )

    optional_requirement_met = (
        total_element_count >= 7
    )


    routine_requirements = (
        routine.routine_requirements
        .select_related(
            'requirement',
        )
        .filter(
            is_met=True,
        )
    )


    cr_total = Decimal('0.00')

    bonus_total = Decimal('0.00')


    for routine_requirement in (
        routine_requirements
    ):

        requirement = (
            routine_requirement.requirement
        )


        if (
            requirement.requirement_type
            ==
            PathwayRequirement.TYPE_BONUS
        ):

            bonus_total += (
                requirement.bonus_value
                or Decimal('0.00')
            )


        elif requirement.is_required:

            cr_total += (
                requirement.value
                or Decimal('0.00')
            )


    projected_d_score = (
        element_dv
        +
        cr_total
        +
        bonus_total
    )


    return {
        'element_dv': element_dv,

        'cr_total': cr_total,

        'bonus_total': bonus_total,

        'projected_d_score': (
            projected_d_score
        ),

        'acro_count': acro_count,

        'dance_count': dance_count,

        'total_element_count': (
            total_element_count
        ),

        'acro_requirement_met': (
            acro_requirement_met
        ),

        'dance_requirement_met': (
            dance_requirement_met
        ),

        'optional_requirement_met': (
            optional_requirement_met
        ),
    }


def calculate_vault_d_score(
    routine,
):
    """
    Projected Vault D score.

    Vault is simpler than Bars/Beam/Floor:
    - use the selected vault element DV
    - add any applicable HP bonus
    """

    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    selected_vault = (
        elements.first()
    )


    if selected_vault:

        vault_dv = (
                selected_vault.vault_value
                or Decimal('0.00')
        )

    else:

        vault_dv = Decimal('0.00')


    routine_requirements = (
        routine.routine_requirements
        .select_related(
            'requirement',
        )
        .filter(
            is_met=True,
        )
    )


    bonus_total = Decimal('0.00')


    for routine_requirement in (
        routine_requirements
    ):

        requirement = (
            routine_requirement.requirement
        )


        if (
            requirement.requirement_type
            ==
            PathwayRequirement.TYPE_BONUS
        ):

            bonus_total += (
                requirement.bonus_value
                or Decimal('0.00')
            )


    projected_d_score = (
        vault_dv
        +
        bonus_total
    )


    return {
        'selected_vault': (
            selected_vault
        ),

        'vault_dv': (
            vault_dv
        ),

        'bonus_total': (
            bonus_total
        ),

        'projected_d_score': (
            projected_d_score
        ),
    }