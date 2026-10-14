from copy import deepcopy
from hashlib import sha256
import json

from django.apps import apps
from django.db.models import Count
from skill_tracker.models import Skill, SkillResult
from skill_tracker.services import normalize
from .models import EventSkillPlan, EVENTS


def current_version(gym_id, athlete):
    versions = list(EventSkillPlan.objects.filter(gym_id=gym_id, athlete=athlete)
                    .order_by('event').values_list('event', 'updated_at'))
    return sha256(json.dumps([(event, stamp.isoformat()) for event, stamp in versions]).encode()).hexdigest()


def current_values(gym_id, athlete, skills):
    available = {(skill.event, skill.key): skill for skill in skills}
    content = {event: {'skills': [], 'minutes': 0, 'routines': 0, 'pressure': 0, 'cue': ''} for event, label in EVENTS}
    for plan in EventSkillPlan.objects.filter(gym_id=gym_id, athlete=athlete):
        item = content[plan.event]
        item['cue'] = plan.training_cues
        for name in plan.skill_names:
            skill = available.get((plan.event, normalize(name).casefold()))
            if skill:
                item['skills'].append({'id': skill.pk, 'name': skill.name, 'target': 0})
    return {'title': 'Daily practice', 'level': '', 'focus': '', 'notes': '', 'content': content}


def snapshot(plan):
    return {field: deepcopy(getattr(plan, field)) for field in ['level', 'focus', 'notes', 'content']}


def form_initial(values, version, tracker_version, skills):
    initial = {key: values.get(key, '') for key in ['title', 'level', 'focus', 'notes']}
    initial.update(version=version, current_version=tracker_version)
    available = {skill.pk: skill for skill in skills}
    for event, label in EVENTS:
        item = values.get('content', {}).get(event, {})
        for field in ['minutes', 'routines', 'pressure', 'cue']:
            initial[event + '_' + field] = item.get(field, '') if field == 'cue' else item.get(field, 0) or ''
        for chosen in item.get('skills', []):
            if chosen.get('id') in available and available[chosen['id']].event == event:
                initial['skill_' + str(chosen['id'])] = True
                initial['target_' + str(chosen['id'])] = chosen.get('target', 0) or ''
    return initial


def sync_current_skills(gym_id, athlete, user, values):
    """Only the selected athlete changes; existing planner signals update Skill Tracker."""
    for event, label in EVENTS:
        item = values['content'][event]
        plan = EventSkillPlan.objects.filter(gym_id=gym_id, athlete=athlete, event=event).first()
        if not plan and not item['skills'] and not item['cue']:
            continue
        plan = plan or EventSkillPlan(gym_id=gym_id, athlete=athlete, event=event)
        plan.skills_text = '\n'.join(skill['name'] for skill in item['skills'])
        plan.training_cues = item['cue']
        plan.updated_by = user
        plan.full_clean()
        plan.save()


def progress_rows(plan):
    if not plan:
        return []
    counts = {row['assignment__skill_id']: row['total'] for row in SkillResult.objects.filter(
        assignment__athlete_id=plan.athlete_id, assignment__skill__gym_id=plan.gym_id,
        practice_date=plan.practice_date,
    ).order_by().values('assignment__skill_id').annotate(total=Count('pk'))}
    routines = {}
    if apps.is_installed('routine_tracker'):
        model = apps.get_model('routine_tracker', 'DailyRoutineAttempt')
        routines = {(row['event'], row['is_pressure']): row['total'] for row in model.objects.filter(
            athlete_id=plan.athlete_id, session__gym_id=plan.gym_id,
            session__practice_date=plan.practice_date,
        ).order_by().values('event', 'is_pressure').annotate(total=Count('pk'))}
    rows = []
    for event, label in EVENTS:
        content = deepcopy(plan.content.get(event, {}))
        for skill in content.get('skills', []):
            skill['completed'] = counts.get(skill['id'], 0)
            skill['met'] = bool(skill.get('target') and skill['completed'] >= skill['target'])
        rows.append({'code': event, 'label': label, **content,
                     'routine_completed': routines.get((event, False), 0),
                     'pressure_completed': routines.get((event, True), 0)})
    return rows
