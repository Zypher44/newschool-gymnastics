"""Read-only, gym-scoped daily and weekly schedule overview."""
from datetime import date, time, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone
from coaches.models import TeamEvent
from practice_planner.models import PracticePlan
from .views import get_director_gym
from gym_scheduling.models import GroupSchedule


def minute(value):
    return value.hour * 60 + value.minute + value.second / 60


def overlaps(start, end, hour):
    # Incomplete or invalid times cannot establish occupancy.
    return bool(start is not None and end is not None and end > start
                and minute(start) < (hour + 1) * 60 and minute(end) > hour * 60)


def build_days(selected, practices, events, today, schedules=()):
    start = selected - timedelta(days=(selected.weekday() + 1) % 7)
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        items = []
        for p in practices:
            if p.practice_date == day:
                items.append({'kind': 'Practice', 'title': p.title,
                              'group': p.training_group.name, 'start': p.start_time,
                              'end': p.end_time})
        for e in events:
            if e.event_date == day:
                items.append({'kind': 'Event', 'title': e.title,
                              'group': e.training_group.name if e.training_group else '',
                              'start': e.start_time, 'end': e.end_time})
        cancelled = []
        for schedule in schedules:
            if schedule.occurs_on(day):
                exception = next((e for e in schedule.exceptions.all() if e.date == day), None)
                item = {'kind': 'Recurring', 'title': 'Scheduled group training',
                        'group': schedule.group.name, 'start': schedule.start_time,
                        'end': schedule.end_time, 'schedule_id': schedule.pk, 'date': day}
                if exception:
                    item['note'] = exception.note
                    if exception.action == 'cancel':
                        item['title'] = 'Cancelled session'
                        cancelled.append(item)
                        continue
                    item.update(title='Changed hours', start=exception.start_time, end=exception.end_time)
                items.append(item)
        items.sort(key=lambda i: (i['start'] or time.min, i['title']))
        hours = [{'label': f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}",
                  'items': [i for i in items if overlaps(i['start'], i['end'], hour)]}
                 for hour in range(24)]
        days.append({'date': day, 'items': items, 'hours': hours, 'cancelled': cancelled,
                     'today': day == today,
                     'untimed': [i for i in items if i['start'] is None or i['end'] is None
                                 or i['end'] <= i['start']]})
    return days


@login_required
def gym_usage(request):
    gym = get_director_gym(request.user)
    if gym is None:
        raise PermissionDenied('An active director membership in one gym is required.')
    today = timezone.localdate()
    try:
        selected = date.fromisoformat(request.GET.get('date', today.isoformat()))
        if not 1901 <= selected.year <= 2099:
            raise ValueError
    except (TypeError, ValueError):
        selected = today
    mode = 'day' if request.GET.get('view') == 'day' else 'week'
    start = selected - timedelta(days=(selected.weekday() + 1) % 7)
    end = start + timedelta(days=6)
    practices = list(PracticePlan.objects.filter(
        training_group__gym=gym, practice_date__range=(start, end),
        status__in=['scheduled', 'in_progress', 'completed'],
    ).select_related('training_group'))
    events = list(TeamEvent.objects.filter(
        gym=gym, event_date__range=(start, end),
    ).select_related('training_group'))
    # A malformed cross-gym event relation must not expose another gym's group.
    for event in events:
        if event.training_group and event.training_group.gym_id != gym.pk:
            event.training_group = None
    schedules = list(GroupSchedule.objects.filter(
        group__gym=gym, group__is_active=True, is_active=True,
        start_date__lte=end, end_date__gte=start,
    ).select_related('group').prefetch_related('exceptions'))
    days = build_days(selected, practices, events, today, schedules)
    current = next(d for d in days if d['date'] == selected)
    visible = days if mode == 'week' else [current]
    items = [item for day in visible for item in day['items']]
    return render(request, 'gyms/gym_usage.html', {
        'gym': gym, 'mode': mode, 'selected': selected,
        'week_start': start, 'week_end': end, 'days': days, 'current': current,
        'previous': selected - timedelta(days=7 if mode == 'week' else 1),
        'next': selected + timedelta(days=7 if mode == 'week' else 1),
        'recurring_count': sum(i['kind'] == 'Recurring' for i in items),
        'practice_count': sum(i['kind'] == 'Practice' for i in items),
        'event_count': sum(i['kind'] == 'Event' for i in items),
    })
