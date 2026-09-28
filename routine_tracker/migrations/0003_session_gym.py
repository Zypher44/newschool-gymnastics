from django.db import migrations, models
import django.db.models.deletion


def backfill_routine_gyms(apps, schema_editor):
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    Session = apps.get_model('routine_tracker', 'DailyRoutineSession')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None
    for session in Session.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else None
        if gym_id is None and session.created_by_id:
            ids = list(Membership.objects.filter(
                user_id=session.created_by_id, is_active=True, gym__is_active=True,
            ).values_list('gym_id', flat=True).distinct()[:2])
            gym_id = ids[0] if len(ids) == 1 else None
        if gym_id:
            Session.objects.filter(pk=session.pk).update(gym_id=gym_id)


class Migration(migrations.Migration):
    dependencies = [('routine_tracker', '0002_alter_dailyroutineattempt_result'),
                    ('gyms', '0001_initial')]
    operations = [
        migrations.AddField(model_name='dailyroutinesession', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='routine_sessions', null=True, blank=True)),
        migrations.AlterField(model_name='dailyroutinesession', name='practice_date', field=models.DateField()),
        migrations.AddConstraint(model_name='dailyroutinesession', constraint=models.UniqueConstraint(
            fields=('gym', 'practice_date'), name='unique_routine_date_per_gym')),
        migrations.RunPython(backfill_routine_gyms, migrations.RunPython.noop),
    ]
