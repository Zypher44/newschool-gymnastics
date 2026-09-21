from gyms.models import GymMembership

from .models import ParentAthleteLink


def get_parent_gym_ids(user):
    """Return active gyms where the user is an active parent."""

    return (
        GymMembership.objects
        .filter(
            user=user,
            role='parent',
            is_active=True,
            gym__is_active=True,
        )
        .values_list('gym_id', flat=True)
        .distinct()
    )


def get_approved_parent_links(user):
    """
    Return usable parent-child links.

    A link is usable only while it is approved, the child is active,
    and both accounts retain active memberships in the same active gym.
    """

    parent_gym_ids = get_parent_gym_ids(user)

    return (
        ParentAthleteLink.objects
        .filter(
            parent=user,
            approved=True,
            athlete__is_active=True,
            athlete__gym_memberships__role='athlete',
            athlete__gym_memberships__is_active=True,
            athlete__gym_memberships__gym__is_active=True,
            athlete__gym_memberships__gym_id__in=parent_gym_ids,
        )
        .select_related('athlete')
        .distinct()
    )


def get_approved_parent_athlete_ids(user):
    """Return athlete IDs the parent is currently authorized to access."""

    return (
        get_approved_parent_links(user)
        .values_list('athlete_id', flat=True)
    )
