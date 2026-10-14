from uuid import uuid4
from django.db import migrations


def import_athlete_results(apps, schema_editor):
    """Queue pre-existing athlete-entered results without changing their saved scores."""
    db = schema_editor.connection.alias
    Tracked = apps.get_model('practice_focus', 'TrackedResult')
    SkillResult = apps.get_model('skill_tracker', 'SkillResult')
    Routine = apps.get_model('routine_tracker', 'DailyRoutineAttempt')
    for result in SkillResult.objects.using(db).filter(recorded_by__role='athlete').select_related('assignment__skill').iterator():
        Tracked.objects.using(db).get_or_create(token=result.token, defaults={
            'gym_id':result.assignment.skill.gym_id,'athlete_id':result.assignment.athlete_id,
            'actor_id':result.recorded_by_id,'practice_date':result.practice_date,'kind':'skill',
            'status':'pending','skill_result_id':result.pk,'details':{'assignment':result.assignment_id,
            'event':result.assignment.skill.event,'label':result.assignment.skill.name,'result':result.result}})
    for result in Routine.objects.using(db).filter(recorded_by__role='athlete',session__gym__isnull=False).select_related('session').iterator():
        Tracked.objects.using(db).get_or_create(routine_result_id=result.pk, defaults={
            'token':uuid4(),'gym_id':result.session.gym_id,'athlete_id':result.athlete_id,
            'actor_id':result.recorded_by_id,'practice_date':result.session.practice_date,'kind':'routine',
            'status':'pending','details':{'event':result.event,'pressure':result.is_pressure,
            'label':result.event.title()+' '+('pressure set' if result.is_pressure else 'routine'),'result':result.result}})


class Migration(migrations.Migration):
    dependencies=[('practice_focus','0004_athletefeedback_trackermutation_personalmilestone_and_more')]
    operations=[migrations.RunPython(import_athlete_results,migrations.RunPython.noop)]
