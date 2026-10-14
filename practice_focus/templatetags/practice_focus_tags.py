from collections import defaultdict
from django import template
from django.apps import apps
from django.db.models import F
from gyms.models import GymMembership
from practice_focus.models import EventSkillPlan
from practice_focus.access import coach_gym_id
from django.core.exceptions import PermissionDenied

register = template.Library()


def visible_plans(request):
    if hasattr(request, '_current_skill_plan_cache'):
        return request._current_skill_plan_cache
    grouped = defaultdict(list)
    user = request.user
    gym_ids = []
    athlete_ids = None
    editable_ids = set()
    if user.is_authenticated and user.is_active:
        if user.role in ['coach', 'head_coach']:
            try:
                gym_ids = [coach_gym_id(user)]
                editable_ids = set(GymMembership.objects.filter(gym_id=gym_ids[0], role='athlete',
                    is_active=True, user__is_active=True, user__role='athlete').values_list('user_id', flat=True))
            except PermissionDenied:
                pass
        elif user.role == 'athlete':
            gym_ids = list(GymMembership.objects.filter(user=user, role='athlete', is_active=True,
                gym__is_active=True).values_list('gym_id', flat=True))
            athlete_ids = [user.pk]
        elif user.role == 'parent':
            gym_ids = list(GymMembership.objects.filter(user=user, role='parent', is_active=True,
                gym__is_active=True).values_list('gym_id', flat=True))
            try:
                link_model = apps.get_model('parents_portal', 'ParentAthleteLink')
                athlete_ids = list(link_model.objects.filter(parent=user, approved=True).values_list('athlete_id', flat=True))
            except LookupError:
                gym_ids = []
                athlete_ids = []
    if gym_ids:
        plans = EventSkillPlan.objects.filter(gym_id__in=gym_ids,
            athlete__is_active=True, athlete__role='athlete',
            athlete__gym_memberships__gym_id=F('gym_id'),
            athlete__gym_memberships__role='athlete',
            athlete__gym_memberships__is_active=True).select_related('gym').distinct()
        if athlete_ids is not None:
            plans = plans.filter(athlete_id__in=athlete_ids)
        for plan in plans:
            if plan.skill_names or plan.training_cues:
                grouped[(plan.athlete_id, plan.event)].append(plan)
    request._current_skill_plan_cache = grouped
    request._current_skill_editable_ids = editable_ids
    return grouped


@register.inclusion_tag('practice_focus/current_skills.html', takes_context=True)
def current_skills(context, athlete, event):
    request = context.get('request')
    if request is None or not getattr(athlete, 'pk', None):
        return {'plans': [], 'can_edit': False}
    plans = visible_plans(request).get((athlete.pk, event), [])
    can_edit = athlete.pk in getattr(request, '_current_skill_editable_ids', set())
    return {'plans': plans, 'can_edit': can_edit, 'athlete_id': athlete.pk, 'multiple_gyms': len(plans) > 1}
