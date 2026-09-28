from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .catalog import EVENTS
from .models import RequirementProgress, XcelRequirementProgress
from .navigation import pathway_navigation
from .views import _single_gym, _visible_athletes
from .xcel_catalog import DIVISIONS, items_for


@login_required
@require_http_methods(['GET', 'POST'])
def division_detail(request, division, athlete_id=None):
    if division not in DIVISIONS:
        raise Http404('Unknown Xcel division')
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

    items = items_for(division)
    item_map = {item['code']: item for item in items}
    if request.method == 'POST':
        if request.user.role not in ('head_coach', 'coach') or athlete is None:
            raise PermissionDenied
        code = request.POST.get('requirement_code', '')
        status = request.POST.get('status', '')
        if code not in item_map or status not in dict(RequirementProgress.STATUS_CHOICES):
            raise PermissionDenied('Invalid assessment')
        XcelRequirementProgress.objects.update_or_create(
            gym_id=gym_id, athlete=athlete, division=division,
            requirement_code=code,
            defaults={
                'event': item_map[code]['event'], 'status': status,
                'updated_by': request.user,
            },
        )
        return redirect('pathway:athlete_xcel_division_detail', athlete_id=athlete.pk, division=division)

    statuses = {}
    if athlete is not None:
        statuses = dict(XcelRequirementProgress.objects.filter(
            gym_id=gym_id, athlete=athlete, division=division,
            requirement_code__in=item_map,
        ).values_list('requirement_code', 'status'))

    groups = [
        {
            'name': event_name,
            'items': [
                {
                    **item,
                    'status': statuses.get(item['code'], 'not_started'),
                    'status_label': dict(RequirementProgress.STATUS_CHOICES)[
                        statuses.get(item['code'], 'not_started')
                    ],
                }
                for item in items if item['event'] == event_code
            ],
        }
        for event_code, event_name in EVENTS
    ]
    return render(request, 'usag_pathway/requirements_detail.html', {
        'division': division, 'division_name': division.title(),
        'program_label': 'USA Gymnastics Xcel',
        'page_title': f'{division.title()} Division',
        'navigation': pathway_navigation(
            DIVISIONS, division,
            'pathway:athlete_xcel_division_detail' if is_athlete_view else 'pathway:xcel_division_detail',
            athlete_id=athlete.pk if athlete else None,
        ),
        'groups': groups, 'athlete': athlete, 'is_athlete_view': is_athlete_view,
        'item_total': len(items),
        'reviewed_total': sum(status == 'ready' for status in statuses.values()),
        'percent': round(100 * sum(status == 'ready' for status in statuses.values()) / len(items)) if items else 0,
    })
