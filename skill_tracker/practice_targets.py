from practice_focus.models import EVENTS
from practice_focus.personal_models import AthletePracticePlan


def attach_practice_targets(assignments, gym_id, athlete_ids, practice_date):
    """Attach targets from each authorized athlete's saved plan for this date."""
    targets = {}
    plans = AthletePracticePlan.objects.filter(
        gym_id=gym_id, athlete_id__in=athlete_ids, practice_date=practice_date,
    ).only('athlete_id', 'content')
    for plan in plans:
        if not isinstance(plan.content, dict):
            continue
        for event, label in EVENTS:
            event_plan = plan.content.get(event, {})
            if not isinstance(event_plan, dict):
                continue
            skills = event_plan.get('skills', [])
            if not isinstance(skills, list):
                continue
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                skill_id, target = skill.get('id'), skill.get('target')
                if type(skill_id) is int and type(target) is int and 1 <= target <= 200:
                    targets[(plan.athlete_id, event, skill_id)] = target
    assignments = list(assignments)
    for assignment in assignments:
        assignment.practice_target = targets.get(
            (assignment.athlete_id, assignment.skill.event, assignment.skill_id), 0,
        ) if assignment.skill.gym_id == gym_id else 0
    return assignments
