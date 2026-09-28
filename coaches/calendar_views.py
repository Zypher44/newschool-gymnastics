import calendar
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
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
    events_by_date = {}
    for event in events:
        events_by_date.setdefault(event.event_date, []).append(event)
    weeks = [[{
        'date': day,
        'in_month': day.month == first.month,
        'events': events_by_date.get(day, []),
        'today': day == today,
    } for day in week] for week in calendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)]
    return render(request, 'coaches/gym_calendar.html', {
        'weeks': weeks, 'events': events, 'month': first,
        'previous_month': previous.strftime('%Y-%m'),
        'next_month': next_month.strftime('%Y-%m'),
        'can_create': request.user.role in ('director', 'coach', 'head_coach'),
    })
