from django import template
from django.urls import reverse
from django.utils import timezone
from practice_hub.access import ROLES, member_gym, practice_scope, group_roster
from practice_hub.models import OnboardingProgress, PracticeSession
from practice_hub.services import link

register = template.Library()


@register.inclusion_tag('practice_hub/welcome.html', takes_context=True)
def practice_hub_welcome(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated or not request.user.is_active or request.user.role not in ROLES:
        return {}
    if request.path in (reverse('practice_hub:onboarding'), reverse('practice_hub:start')):
        return {}
    gym = member_gym(request.user)
    if gym is None and request.session.get('practice_hub_dismissed_' + request.user.role):
        return {}
    progress = OnboardingProgress.objects.filter(user=request.user, gym=gym,
        role=request.user.role).first() if gym else None
    if progress and (progress.completed_at or progress.dismissed_at):
        return {}
    return {'show': True, 'ready': bool(gym), 'started': bool(progress),
        'url': reverse('practice_hub:onboarding'),
        'next': request.get_full_path(), 'csrf_token': context.get('csrf_token')}


@register.inclusion_tag('practice_hub/tracker_context.html', takes_context=True)
def practice_hub_tracker_context(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated or request.user.role not in ('coach', 'head_coach'):
        return {}
    namespace = request.resolver_match.namespace if request.resolver_match else ''
    if namespace not in ('routine_tracker', 'skill_tracker'):
        return {}
    try:
        session_id = int(request.GET.get('practice_session', ''))
    except (ValueError, TypeError):
        return {}
    gym_id, athletes, groups = practice_scope(request.user)
    session = PracticeSession.objects.filter(pk=session_id, gym_id=gym_id, coach=request.user,
        practice_date=timezone.localdate(), group__in=groups, finished_at__isnull=True).select_related('group').first()
    if not session:
        return {}
    roster = group_roster(athletes, session.group)
    try:
        athlete_id = int(request.GET.get('athlete', ''))
    except (ValueError, TypeError):
        return {}
    if not roster.filter(pk=athlete_id).exists():
        return {}
    event = request.GET.get('event') or session.event
    from practice_focus.models import EVENTS
    if event not in dict(EVENTS):
        return {}
    if namespace == 'routine_tracker':
        # Routine Tracker supports older dates, but an active practice does not.
        tracker_day = request.GET.get('date')
        if tracker_day and tracker_day != session.practice_date.isoformat():
            return {}
    payload = {'kind': 'skill' if namespace == 'skill_tracker' else 'routine',
        'group': str(session.group_id), 'athlete': str(athlete_id), 'event': event,
        'allowed_athletes': [str(pk) for pk in roster.values_list('pk', flat=True)],
        'back_url': link('practice_hub:start', group=session.group_id, athlete=athlete_id, event=event)}
    return {'payload': payload, 'group_name': session.group.name, 'event_label': dict(EVENTS)[event]}
