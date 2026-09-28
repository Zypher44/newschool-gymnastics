from django.db import migrations, models
import django.db.models.deletion


def backfill_planner_gyms(apps, schema_editor):
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    Group = apps.get_model('practice_planner', 'TrainingGroup')
    Template = apps.get_model('practice_planner', 'PracticeTemplate')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None
    for group in Group.objects.filter(gym__isnull=True).iterator():
        coach_ids = list(group.coaches.values_list('pk', flat=True))
        gym_ids = set(Membership.objects.filter(
            user_id__in=coach_ids, is_active=True, gym__is_active=True,
        ).values_list('gym_id', flat=True).distinct())
        gym_id = only_gym.pk if only_gym else (next(iter(gym_ids)) if len(gym_ids) == 1 else None)
        if gym_id:
            Group.objects.filter(pk=group.pk).update(gym_id=gym_id)
    for template in Template.objects.filter(gym__isnull=True).iterator():
        if template.source_practice_id:
            gym_id = Group.objects.filter(
                practice_plans__pk=template.source_practice_id,
            ).values_list('gym_id', flat=True).first()
        else:
            gym_id = only_gym.pk if only_gym else None
        if gym_id:
            Template.objects.filter(pk=template.pk).update(gym_id=gym_id)


class Migration(migrations.Migration):
    dependencies = [('practice_planner', '0003_practicetemplate_practicetemplaterotation_and_more'),
                    ('gyms', '0001_initial')]
    operations = [
        migrations.AddField(model_name='traininggroup', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='planner_groups', null=True, blank=True)),
        migrations.AddField(model_name='practicetemplate', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='practice_templates', null=True, blank=True)),
        migrations.AlterField(model_name='traininggroup', name='name', field=models.CharField(max_length=120)),
        migrations.AddConstraint(model_name='traininggroup', constraint=models.UniqueConstraint(
            fields=('gym', 'name'), name='unique_planner_group_name_per_gym')),
        migrations.RunPython(backfill_planner_gyms, migrations.RunPython.noop),
    ]
