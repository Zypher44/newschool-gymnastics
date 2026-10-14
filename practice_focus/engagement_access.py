from django.core.exceptions import PermissionDenied
from django.db.models import Q
from gyms.tenant import single_active_gym_id
from parents_portal.models import ParentAthleteLink
from .access import coach_gym_id, gym_athletes


def coach_roster(user):
    gym_id = coach_gym_id(user)
    athletes = gym_athletes(gym_id)
    if user.role != 'head_coach':
        athletes = athletes.filter(
            Q(assigned_coaches__coach=user) |
            Q(training_groups__is_active=True, training_groups__group__is_active=True,
              training_groups__group__gym_id=gym_id, training_groups__group__coach_assignments__coach=user)
        ).distinct()
    return gym_id, athletes


def family_roster(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied('Active account required.')
    if user.role == 'athlete':
        gym_id = single_active_gym_id(user, ['athlete'])
        if gym_id is None:
            raise PermissionDenied('A single active athlete gym is required.')
        return gym_id, gym_athletes(gym_id).filter(pk=user.pk)
    if user.role != 'parent':
        raise PermissionDenied('Parent or athlete access required.')
    gym_id = single_active_gym_id(user, ['parent'])
    if gym_id is None:
        raise PermissionDenied('A single active parent gym is required.')
    approved = ParentAthleteLink.objects.filter(parent=user, approved=True).values('athlete_id')
    return gym_id, gym_athletes(gym_id).filter(pk__in=approved)


def tracker_roster(user):
    if user.role in ('coach', 'head_coach'):
        gym_id = coach_gym_id(user)
        return gym_id, gym_athletes(gym_id)
    if user.role == 'athlete':
        return family_roster(user)
    raise PermissionDenied('Coach or athlete access required.')
