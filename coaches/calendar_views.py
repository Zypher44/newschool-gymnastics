import calendar
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from coaches.audiences import visible_events
from gyms.tenant import single_active_gym_id


@login_required
def gym_calendar(request):
    gym_id = single_active_gym_id(request.user, [request.user.role])
    if gym_id is None or request.user.role not in ('director', 'coach', 'head_coach', 'parent', 'athlete'):
        raise Http404

    today = timezone.localdate()
    try:
        year, month = map(int, request.GET.get('month', '').split('-'))
        if not 1900 <= year <= 2100:
            raise ValueError
        first = date(year, month, 1)
    except (ValueError, TypeError):
        first = today.replace(day=1)
    next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    previous = first - timedelta(days=1)
    events = list(visible_events(request.user).filter(
        event_date__gte=first, event_date__lt=next_month,
    ).select_related('training_group').order_by('event_date', 'start_time'))
    from parents_portal.models import PracticeAbsenceNotice
    from parents_portal.selection import selected_child
    from practice_focus.engagement_access import coach_roster
    notices = PracticeAbsenceNotice.objects.filter(gym_id=gym_id, practice_date__gte=first,
        practice_date__lt=next_month).exclude(status='cancelled').select_related('athlete', 'updated_by')
    if request.user.role == 'parent':
        child = selected_child(request)
        notices = notices.filter(athlete=child) if child else notices.none()
        if child:
            from gyms.models import TrainingGroupAthlete
            groups = TrainingGroupAthlete.objects.filter(athlete=child, is_active=True, group__is_active=True).values_list('group_id', flat=True)
            events = [event for event in events if event.audience != 'group' or event.training_group_id in groups]
    elif request.user.role in ('coach', 'head_coach'):
        notices = notices.filter(athlete__in=coach_roster(request.user)[1])
    elif request.user.role != 'director':
        notices = notices.none()
    notices = list(notices)
    notices_by_date = {}
    for notice in notices: notices_by_date.setdefault(notice.practice_date, []).append(notice)
    events_by_date = {}
    for event in events:
        events_by_date.setdefault(event.event_date, []).append(event)
    weeks = [[{
        'date': day,
        'in_month': day.month == first.month,
        'events': events_by_date.get(day, []),
        'notices': notices_by_date.get(day, []),
        'today': day == today,
    } for day in week] for week in calendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)]
    return render(request, 'coaches/gym_calendar.html', {
        'weeks': weeks, 'events': events, 'notices': notices, 'month': first,
        'previous_month': previous.strftime('%Y-%m'),
        'next_month': next_month.strftime('%Y-%m'),
        'can_create': request.user.role in ('director', 'coach', 'head_coach'),
    })
