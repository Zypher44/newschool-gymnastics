from .models import GymMembership


def single_active_gym_id(user, roles=None):
    """Return one active membership's gym; ambiguous or absent means no access."""
    if not user.is_authenticated:
        return None
    memberships = GymMembership.objects.filter(
        user=user, is_active=True, gym__is_active=True,
    )
    if roles is not None:
        memberships = memberships.filter(role__in=roles)
    ids = list(memberships.values_list('gym_id', flat=True).distinct()[:2])
    return ids[0] if len(ids) == 1 else None
