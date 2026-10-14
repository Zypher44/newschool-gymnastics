from django.db.models.signals import post_save
from django.dispatch import receiver
from practice_focus.models import EventSkillPlan
from .services import sync_plan

@receiver(post_save, sender=EventSkillPlan, dispatch_uid='skill_tracker.sync_plan')
def planner_saved(sender, instance, raw=False, using='default', **kwargs):
    if not raw:
        sync_plan(instance, using)
