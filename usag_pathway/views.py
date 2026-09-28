from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from coaches.models import CoachAthleteAssignment
from gyms.models import GymMembership
from parents_portal.models import ParentAthleteLink

from .catalog import CATALOG, EVENTS, items_for, track_for
from .models import RequirementProgress
from .navigation import pathway_navigation


def _single_gym(user):
    """Fail closed for users with missing or ambiguous active gym memberships."""
    gym_ids = list(GymMembership.objects.filter(
        user=user, is_active=True, role=user.role,
        gym__is_active=True,
    ).values_list('gym_id', flat=True).distinct()[:2])
    return gym_ids[0] if len(gym_ids) == 1 else None


def _visible_athletes(user, gym_id):
    athletes = User.objects.filter(
        role='athlete', gym_memberships__gym_id=gym_id,
        gym_memberships__role='athlete', gym_memberships__is_active=True,
    ).distinct()
    if user.role == 'athlete':
        return athletes.filter(pk=user.pk)
    if user.role == 'parent':
        approved_ids = ParentAthleteLink.objects.filter(
            parent=user, approved=True,
        ).values_list('athlete_id', flat=True)
        return athletes.filter(pk__in=approved_ids)
    if user.role == 'coach':
        assigned_ids = CoachAthleteAssignment.objects.filter(
            coach=user,
        ).values_list('athlete_id', flat=True)
        return athletes.filter(pk__in=assigned_ids)
    if user.role in ('head_coach', 'director'):
        return athletes
    return athletes.none()


@login_required
@require_http_methods(['GET', 'POST'])
def level_detail(request, level, athlete_id=None):
    if level not in CATALOG:
        raise Http404('Unknown USAG level')
    if request.user.role not in ('director', 'head_coach', 'coach', 'athlete', 'parent'):
        raise PermissionDenied

    gym_id = _single_gym(request.user)
    if gym_id is None:
        raise PermissionDenied('An active membership in one gym is required.')

    is_athlete_view = athlete_id is not None
    if is_athlete_view:
        if request.user.role not in ('head_coach', 'coach'):
            raise PermissionDenied('Only coaches can assess requirements.')
        athlete = get_object_or_404(_visible_athletes(request.user, gym_id), pk=athlete_id)
    else:
        if request.method == 'POST':
            raise PermissionDenied('The general pathway is read-only.')
        athlete = None

    items = items_for(level)
    item_map = {item['code']: item for item in items}
    if request.method == 'POST':
        if request.user.role not in ('head_coach', 'coach'):
            raise PermissionDenied('Only coaches can assess requirements.')
        if athlete is None:
            raise PermissionDenied
        code = request.POST.get('requirement_code', '')
        status = request.POST.get('status', '')
        if code not in item_map or status not in dict(RequirementProgress.STATUS_CHOICES):
            raise PermissionDenied('Invalid assessment.')
        RequirementProgress.objects.update_or_create(
            gym_id=gym_id, athlete=athlete, level=level,
            requirement_code=code,
            defaults={
                'event': item_map[code]['event'], 'status': status,
                'updated_by': request.user,
            },
        )
        return redirect('pathway:athlete_usag_level_detail', athlete_id=athlete.pk, level=level)

    status_by_code = {}
    if athlete is not None:
        status_by_code = dict(RequirementProgress.objects.filter(
            gym_id=gym_id, athlete=athlete, level=level,
            requirement_code__in=item_map,
        ).values_list('requirement_code', 'status'))

    groups = []
    reviewed_total = 0
    for event_code, event_name in EVENTS:
        event_items = []
        for item in items:
            if item['event'] != event_code:
                continue
            status = status_by_code.get(item['code'], 'not_started')
            reviewed_total += status == 'ready'
            event_items.append({
                **item, 'status': status,
                'status_label': dict(RequirementProgress.STATUS_CHOICES)[status],
            })
        groups.append({'name': event_name, 'items': event_items})

    program = 'USAG Compulsory' if level <= 5 else 'USAG Optional'
    level_range = range(1, 6) if level <= 5 else range(6, 11)
    return render(request, 'usag_pathway/requirements_detail.html', {
        'level': level, 'track': track_for(level), 'groups': groups,
        'program_label': program, 'page_title': f'Level {level}',
        'navigation': pathway_navigation(
            level_range, level,
            'pathway:athlete_usag_level_detail' if is_athlete_view else 'pathway:usag_level_detail',
            athlete_id=athlete.pk if athlete else None,
        ),
        'athlete': athlete, 'is_athlete_view': is_athlete_view,
        'percent': round(reviewed_total / len(items) * 100),
        'reviewed_total': reviewed_total, 'item_total': len(items),
    })
