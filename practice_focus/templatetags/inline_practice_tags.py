from django import template
from django.urls import reverse
from django.utils import timezone
from practice_focus.engagement_access import tracker_roster
from practice_focus.engagement_services import daily_counts
from practice_focus.models import AthletePracticePlan, EVENTS
from skill_tracker.models import Assignment
from skill_tracker.practice_targets import attach_practice_targets

register = template.Library()


def target(value):
    return value if type(value) is int and 0 <= value <= 200 else 0


@register.inclusion_tag('practice_focus/inline_trackers.html', takes_context=True)
def inline_practice_trackers(context, athlete, day, event='', finished=False):
    request = context.get('request')
    if not request or not athlete or not request.user.is_authenticated or not request.user.is_active:
        return {}
    if request.user.role not in ('coach', 'head_coach', 'athlete'):
        return {}
    gym_id, roster = tracker_roster(request.user)
    if not roster.filter(pk=athlete.pk).exists():
        return {}
    plan = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete=athlete, practice_date=day).first()
    content = plan.content if plan and isinstance(plan.content, dict) else {}
    assignments = attach_practice_targets(Assignment.objects.filter(athlete=athlete,
        skill__gym_id=gym_id, is_active=True).select_related('skill').order_by('skill__name', 'pk'),
        gym_id, [athlete.pk], day)
    rows = []
    for code, label in EVENTS:
        event_plan = content.get(code, {})
        if not isinstance(event_plan, dict):
            event_plan = {}
        rows.append({'code': code, 'label': label, 'cue': str(event_plan.get('cue') or ''),
            'skills': [{'id': str(a.pk), 'name': a.skill.name, 'target': a.practice_target}
                for a in assignments if a.skill.event == code],
            'routine_target': target(event_plan.get('routines')), 'pressure_target': target(event_plan.get('pressure'))})
    # A planner view starts with an event that has work assigned, while Start Practice uses its selected event.
    selected = event if event in dict(EVENTS) else next((r['code'] for r in rows
        if r['skills'] or r['routine_target'] or r['pressure_target']), 'floor')
    enabled = day == timezone.localdate() and not finished
    reason = 'Practice finished. Resume practice to record more results.' if finished else (
        'Results can be recorded here on the practice date.' if not enabled else '')
    data = {'gym': str(gym_id), 'user': str(request.user.pk), 'athlete': str(athlete.pk),
        'name': athlete.get_full_name() or athlete.username, 'date': day.isoformat(),
        'event': selected, 'events': rows, 'enabled': enabled,
        'counts': daily_counts(gym_id, athlete.pk, day),
        'save_url': reverse('practice_focus:tracker_mutate'), 'state_url': reverse('practice_focus:tracker_state')}
    return {'show': True, 'tracking': data, 'inline_events': rows, 'inline_event': selected,
            'inline_enabled': enabled, 'inline_reason': reason, 'inline_external_events': bool(event)}
