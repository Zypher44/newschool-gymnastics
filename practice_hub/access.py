from django.core.exceptions import PermissionDenied
from django.db.models import Q
from gyms.models import Gym, TrainingGroup
from gyms.tenant import single_active_gym_id
from practice_focus.engagement_access import coach_roster

ROLES = ('director', 'head_coach', 'coach', 'athlete', 'parent')


def member_gym(user):
    if not user.is_authenticated or not user.is_active or user.role not in ROLES:
        return None
    gym_id = single_active_gym_id(user, [user.role])
    return Gym.objects.filter(pk=gym_id, is_active=True).first() if gym_id else None


def practice_scope(user):
    gym_id, athletes = coach_roster(user)
    groups = TrainingGroup.objects.filter(gym_id=gym_id, is_active=True)
    if user.role != 'head_coach':
        groups = groups.filter(Q(coach_assignments__coach=user) |
            Q(athlete_assignments__athlete__in=athletes, athlete_assignments__is_active=True))
    return gym_id, athletes, groups.distinct().order_by('name', 'pk')


def group_roster(athletes, group):
    return athletes.filter(training_groups__group=group, training_groups__is_active=True).distinct()
