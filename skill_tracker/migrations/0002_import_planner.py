from django.db import migrations


def import_plans(apps, schema_editor):
    Plan = apps.get_model('practice_focus', 'EventSkillPlan')
    Skill = apps.get_model('skill_tracker', 'Skill')
    Assignment = apps.get_model('skill_tracker', 'Assignment')
    db = schema_editor.connection.alias
    for plan in Plan.objects.using(db).all().iterator():
        for line in plan.skills_text.splitlines():
            name = ' '.join(line.split())
            if not name:
                continue
            skill, _ = Skill.objects.using(db).get_or_create(gym_id=plan.gym_id,
                event=plan.event, key=name.casefold(), defaults={'name': name})
            Assignment.objects.using(db).get_or_create(skill_id=skill.pk, athlete_id=plan.athlete_id)


class Migration(migrations.Migration):
    dependencies = [('skill_tracker', '0001_initial'), ('practice_focus', '0001_initial')]
    operations = [migrations.RunPython(import_plans, migrations.RunPython.noop)]
