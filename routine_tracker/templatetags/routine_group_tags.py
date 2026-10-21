from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def routine_training_groups(context):
    """Return this routine session's groups and already-authorized athletes."""
    from gyms.models import TrainingGroup, TrainingGroupAthlete

    session = context.get("session")
    gym_id = getattr(session, "gym_id", None)
    if not gym_id:
        return []

    allowed_ids = {
        row["athlete"].pk
        for row in context.get("athlete_rows", [])
    }
    groups = list(
        TrainingGroup.objects.filter(gym_id=gym_id, is_active=True)
        .order_by("name", "pk")
        .values("id", "name")
    )
    members = {group["id"]: [] for group in groups}
    assignments = TrainingGroupAthlete.objects.filter(
        group_id__in=members,
        is_active=True,
        athlete_id__in=allowed_ids,
        athlete__is_active=True,
        athlete__gym_memberships__gym_id=gym_id,
        athlete__gym_memberships__role="athlete",
        athlete__gym_memberships__is_active=True,
    ).values_list("group_id", "athlete_id").distinct()
    for group_id, athlete_id in assignments:
        members[group_id].append(str(athlete_id))

    return [
        {"id": str(group["id"]), "name": group["name"],
         "athlete_ids": members[group["id"]]}
        for group in groups
    ]
