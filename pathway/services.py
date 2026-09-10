from .models import (
    AthletePathwayRequirement,
    PathwayRequirement,
)


def sync_athlete_pathway_requirements(
    athlete_pathway,
):
    """
    Ensure the athlete has individual requirement records
    for the current and target pathway levels.

    Existing athlete progress is preserved.
    """

    level_ids = set()

    if athlete_pathway.current_level_id:
        level_ids.add(
            athlete_pathway.current_level_id
        )

    if athlete_pathway.target_level_id:
        level_ids.add(
            athlete_pathway.target_level_id
        )

    if not level_ids:
        return {
            'created': 0,
            'existing': 0,
        }

    requirements = (
        PathwayRequirement.objects
        .filter(
            level_id__in=level_ids,
            is_active=True,
        )
        .select_related(
            'level',
            'event',
        )
        .order_by(
            'level__order',
            'event__order',
            'display_order',
        )
    )

    created_count = 0
    existing_count = 0

    for requirement in requirements:

        athlete_requirement, created = (
            AthletePathwayRequirement.objects
            .get_or_create(
                athlete_pathway=athlete_pathway,
                requirement=requirement,
            )
        )

        if created:
            created_count += 1

        else:
            existing_count += 1

    return {
        'created': created_count,
        'existing': existing_count,
    }