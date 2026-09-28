"""Gym scoped audiences for calendar events and announcements."""

from django.db.models import Q

from accounts.models import User
from gyms.models import GymMembership, TrainingGroup, TrainingGroupAthlete
from gyms.tenant import single_active_gym_id
from parents_portal.models import ParentAthleteLink


def selectable_groups(user):
    gym_id = single_active_gym_id(user, [user.role])
    groups = TrainingGroup.objects.filter(gym_id=gym_id, is_active=True)
    if user.role in ('coach', 'head_coach'):
        groups = groups.filter(coach_assignments__coach=user)
    elif user.role != 'director':
        return groups.none()
    return groups.distinct().order_by('name')


def requested_event_audience(request):
    """Validate the requested audience and its group against the author."""
    audience = request.POST.get('audience', 'all')
    if audience not in ('all', 'coaches', 'parents', 'group'):
        raise ValueError('Choose a valid event audience.')
    group = None
    if audience == 'group':
        group_id = request.POST.get('training_group', '')
        if not group_id.isdigit():
            raise ValueError('Choose a training group assigned to you.')
        group = selectable_groups(request.user).filter(
            pk=group_id,
        ).first()
        if group is None:
            raise ValueError('Choose a training group assigned to you.')
    return audience, group


def audience_members(user, audience, group=None):
    """Active recipients in the sender's gym, including linked group parents."""
    gym_id = single_active_gym_id(user, [user.role])
    if gym_id is None or user.role not in ('director', 'coach', 'head_coach'):
        return User.objects.none()
    members = User.objects.filter(
        gym_memberships__gym_id=gym_id,
        gym_memberships__is_active=True,
        gym_memberships__role__in=['director', 'coach', 'head_coach', 'athlete', 'parent'],
        role__in=['director', 'coach', 'head_coach', 'athlete', 'parent'],
        is_active=True,
    ).exclude(pk=user.pk)
    if audience == 'coaches':
        members = members.filter(role__in=['coach', 'head_coach'])
    elif audience == 'parents':
        members = members.filter(role='parent')
    elif audience == 'group':
        if group is None or not selectable_groups(user).filter(pk=group.pk).exists():
            return User.objects.none()
        athlete_ids = TrainingGroupAthlete.objects.filter(
            group=group, is_active=True,
        ).values_list('athlete_id', flat=True)
        parent_ids = ParentAthleteLink.objects.filter(
            athlete_id__in=athlete_ids, approved=True,
        ).values_list('parent_id', flat=True)
        members = members.filter(
            Q(pk__in=athlete_ids) | Q(pk__in=parent_ids)
            | Q(training_group_assignments__group=group)
        )
    elif audience != 'all':
        return User.objects.none()
    return members.distinct().order_by('role', 'first_name', 'username')


def visible_events(user):
    """Calendar items addressed to this member; includes legacy gym events."""
    from coaches.models import TeamEvent

    gym_id = single_active_gym_id(user, [user.role])
    if gym_id is None or user.role not in ('director', 'coach', 'head_coach', 'parent', 'athlete'):
        return TeamEvent.objects.none()
    events = TeamEvent.objects.filter(gym_id=gym_id)
    if user.role == 'director':
        return events
    role_audience = Q(audience='all')
    if user.role in ('coach', 'head_coach'):
        role_audience |= Q(audience='coaches')
        group_ids = TrainingGroup.objects.filter(
            gym_id=gym_id, coach_assignments__coach=user, is_active=True,
        ).values('pk')
    elif user.role == 'parent':
        role_audience |= Q(audience='parents')
        athlete_ids = ParentAthleteLink.objects.filter(
            parent=user, approved=True,
            athlete__gym_memberships__gym_id=gym_id,
            athlete__gym_memberships__role='athlete',
            athlete__gym_memberships__is_active=True,
        ).values('athlete_id')
        group_ids = TrainingGroupAthlete.objects.filter(
            athlete_id__in=athlete_ids, is_active=True,
            group__gym_id=gym_id, group__is_active=True,
        ).values('group_id')
    else:
        group_ids = TrainingGroupAthlete.objects.filter(
            athlete=user, is_active=True,
            group__gym_id=gym_id, group__is_active=True,
        ).values('group_id')
    return events.filter(role_audience | Q(audience='group', training_group_id__in=group_ids)).distinct()
