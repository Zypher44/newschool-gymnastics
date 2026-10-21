from django import template
from django.core.exceptions import PermissionDenied

register = template.Library()


def visible_targets(context):
    """Scope plans to the session, active gym membership, and the existing roster."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    session = context.get('session')
    gym_id = getattr(session, 'gym_id', None)
    day = getattr(session, 'practice_date', None) or context.get('practice_date')
    role = getattr(user, 'role', None)
    if not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False) or not gym_id or not day:
        return {}
    if role not in ('coach', 'head_coach', 'athlete'):
        return {}
    allowed = {row['athlete'].pk for row in context.get('athlete_rows', [])}
    if role == 'athlete':
        allowed &= {user.pk}
    key = (user.pk, role, gym_id, str(day), tuple(sorted(allowed)))
    cached = getattr(request, '_routine_plan_target_cache', None)
    if cached and cached['key'] == key:
        return cached['values']
    values = {}
    try:
        if role in ('coach', 'head_coach'):
            from practice_focus.access import coach_gym_id
            if coach_gym_id(user) != gym_id:
                raise PermissionDenied
        else:
            from gyms.models import GymMembership
            memberships = list(GymMembership.objects.filter(user=user, role='athlete',
                is_active=True, gym__is_active=True).values_list('gym_id', flat=True).distinct()[:2])
            if memberships != [gym_id]:
                raise PermissionDenied
        if allowed:
            from practice_focus.personal_models import AthletePracticePlan
            from practice_focus.models import EVENTS
            plans = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete_id__in=allowed,
                practice_date=day, gym__is_active=True,
                athlete__is_active=True, athlete__role='athlete',
                athlete__gym_memberships__gym_id=gym_id,
                athlete__gym_memberships__role='athlete',
                athlete__gym_memberships__is_active=True,
            ).only('athlete_id', 'content').distinct()
            for plan in plans:
                if not isinstance(plan.content, dict):
                    continue
                for event, label in EVENTS:
                    item = plan.content.get(event, {})
                    if not isinstance(item, dict):
                        continue
                    for pressure, field in [(False, 'routines'), (True, 'pressure')]:
                        target = item.get(field, 0)
                        if type(target) is int and 1 <= target <= 100:
                            values[(plan.athlete_id, event, pressure)] = target
    except PermissionDenied:
        pass
    request._routine_plan_target_cache = {'key': key, 'values': values}
    return values


@register.inclusion_tag('routine_tracker/routine_target.html', takes_context=True)
def routine_plan_target(context, athlete, event, is_pressure):
    target = visible_targets(context).get((athlete.pk, event, bool(is_pressure)), 0)
    kind = 'pressure set' if is_pressure else 'routine attempt'
    return {'target': target, 'kind': kind if target == 1 else kind + 's'}
