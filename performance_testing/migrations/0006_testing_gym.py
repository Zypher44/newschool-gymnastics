from django.db import migrations, models
import django.db.models.deletion


def backfill_testing_gyms(apps, schema_editor):
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    Group = apps.get_model('gyms', 'TrainingGroup')
    Exercise = apps.get_model('performance_testing', 'TestingExercise')
    Session = apps.get_model('performance_testing', 'TestingSession')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None

    def creator_gym(user_id):
        if not user_id:
            return None
        ids = list(Membership.objects.filter(
            user_id=user_id, is_active=True, gym__is_active=True,
        ).values_list('gym_id', flat=True).distinct()[:2])
        return ids[0] if len(ids) == 1 else None

    for exercise in Exercise.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else creator_gym(exercise.created_by_id)
        if gym_id:
            Exercise.objects.filter(pk=exercise.pk).update(gym_id=gym_id)
    for session in Session.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else None
        if gym_id is None:
            candidates = set()
            if session.training_group_id:
                group_gym = Group.objects.filter(pk=session.training_group_id).values_list('gym_id', flat=True).first()
                if group_gym:
                    candidates.add(group_gym)
            author_gym = creator_gym(session.created_by_id)
            if author_gym:
                candidates.add(author_gym)
            gym_id = next(iter(candidates)) if len(candidates) == 1 else None
        if gym_id:
            Session.objects.filter(pk=session.pk).update(gym_id=gym_id)


class Migration(migrations.Migration):
    dependencies = [('performance_testing', '0005_alter_testingsession_training_group'),
                    ('gyms', '0001_initial')]
    operations = [
        migrations.AddField(model_name='testingexercise', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='testing_exercises', null=True, blank=True)),
        migrations.AddField(model_name='testingsession', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='performance_sessions', null=True, blank=True)),
        migrations.RunPython(backfill_testing_gyms, migrations.RunPython.noop),
    ]
