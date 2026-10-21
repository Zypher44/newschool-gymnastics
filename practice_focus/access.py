from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from gyms.models import GymMembership


def coach_gym_id(user):
    if not user.is_authenticated or not user.is_active or user.role not in ['coach', 'head_coach']:
        raise PermissionDenied('Only coaches and head coaches can manage current skills.')
    gym_ids = list(GymMembership.objects.filter(user=user, role__in=['coach', 'head_coach'],
        is_active=True, gym__is_active=True).values_list('gym_id', flat=True).distinct()[:2])
    if len(gym_ids) != 1:
        raise PermissionDenied('A single active coaching gym is required.')
    return gym_ids[0]


def gym_athletes(gym_id):
    return get_user_model().objects.filter(role='athlete', is_active=True,
        gym_memberships__gym_id=gym_id, gym_memberships__role='athlete',
        gym_memberships__is_active=True).distinct().order_by('first_name', 'last_name', 'username')
