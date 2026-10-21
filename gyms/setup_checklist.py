"""Read-only, live setup checks for the director's active gym roster."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from parents_portal.models import ParentAthleteLink
from .models import GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from .views import get_director_gym

ROLES = ('athlete', 'parent', 'coach', 'head_coach')


def completion_checklist(gym):
    memberships = list(GymMembership.objects.filter(gym=gym, is_active=True,
        user__is_active=True, role__in=ROLES, user__role__in=ROLES,
        user__is_staff=False, user__is_superuser=False).select_related('user').order_by(
            'user__first_name', 'user__last_name', 'user__username', 'pk'))
    memberships = [m for m in memberships if m.role == m.user.role]
    ids = {m.user_id for m in memberships}
    parent_ids = {m.user_id for m in memberships if m.role == 'parent'}
    linked = set(ParentAthleteLink.objects.filter(parent_id__in=parent_ids,
        athlete_id__in=ids, approved=True).values_list('athlete_id', flat=True))
    grouped_athletes = set(TrainingGroupAthlete.objects.filter(group__gym=gym,
        group__is_active=True, is_active=True, athlete_id__in=ids).values_list('athlete_id', flat=True))
    grouped_coaches = set(TrainingGroupCoach.objects.filter(group__gym=gym,
        group__is_active=True, coach_id__in=ids).values_list('coach_id', flat=True))
    shared = set(GymMembership.objects.filter(user_id__in=ids, is_active=True,
        gym__is_active=True).exclude(gym=gym).values_list('user_id', flat=True))
    buckets = {'passwords': [], 'parents': [], 'groups': []}
    for membership in memberships:
        user = membership.user
        row = {'id': user.pk, 'membership_id': membership.pk,
            'name': user.get_full_name().strip() or user.username, 'username': user.username,
            'role': user.get_role_display(), 'role_code': user.role,
            'edit_url': reverse('edit_gym_person', args=[membership.pk])}
        if not user.has_usable_password():
            buckets['passwords'].append({**row, 'shared': user.pk in shared,
                'action_url': reverse('reset_gym_person_password', args=[membership.pk]) if user.pk not in shared else ''})
        if user.role == 'athlete' and user.pk not in linked:
            buckets['parents'].append({**row, 'action_url': reverse('link_parent_guardian', args=[user.pk])})
        grouped = grouped_athletes if user.role == 'athlete' else grouped_coaches
        if user.role != 'parent' and user.pk not in grouped:
            buckets['groups'].append(row)
    checks = [
        {'key': 'passwords', 'title': 'Accounts needing a password', 'count': len(buckets['passwords']),
         'description': 'Active accounts that do not yet have a usable password.'},
        {'key': 'parents', 'title': 'Athletes without an approved parent', 'count': len(buckets['parents']),
         'description': 'An active parent account in this gym must have an approved connection.'},
        {'key': 'groups', 'title': 'Athletes and coaches without a group', 'count': len(buckets['groups']),
         'description': 'An active training group is required for this check. Parents do not need a group.'},
    ]
    return {'people_count': len(memberships), 'checks': checks, 'buckets': buckets,
        'complete': bool(memberships) and not any(check['count'] for check in checks)}


@login_required
@never_cache
@require_GET
def setup_checklist(request):
    gym = get_director_gym(request.user)
    if gym is None or not request.user.is_active:
        raise Http404
    checklist = completion_checklist(gym)
    selected = request.GET.get('check')
    if selected not in checklist['buckets']:
        selected = next((check['key'] for check in checklist['checks'] if check['count']), 'passwords')
    check = next(check for check in checklist['checks'] if check['key'] == selected)
    page = Paginator(checklist['buckets'][selected], 25).get_page(request.GET.get('page'))
    groups = TrainingGroup.objects.filter(gym=gym, is_active=True).order_by('name') if selected == 'groups' else []
    return render(request, 'gyms/setup_checklist.html', {'gym': gym, 'setup_checklist': checklist,
        'selected_check': check, 'page': page, 'groups': groups})
