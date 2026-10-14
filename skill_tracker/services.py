from django.db import transaction
from .models import Skill, Assignment

def normalize(name):
    return ' '.join(name.split())

def sync_plan(plan, using='default'):
    """The existing planner remains the source of current assignments."""
    with transaction.atomic(using=using):
        ids = []
        for line in plan.skills_text.splitlines():
            name = normalize(line)
            if not name:
                continue
            skill, _ = Skill.objects.using(using).get_or_create(gym_id=plan.gym_id,
                event=plan.event, key=name.casefold(), defaults={'name': name})
            assignment, _ = Assignment.objects.using(using).update_or_create(
                skill=skill, athlete_id=plan.athlete_id, defaults={'is_active': True})
            ids.append(assignment.pk)
        Assignment.objects.using(using).filter(athlete_id=plan.athlete_id,
            skill__gym_id=plan.gym_id, skill__event=plan.event).exclude(pk__in=ids).update(is_active=False)
