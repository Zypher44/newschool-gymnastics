from django.db import migrations, models
import django.db.models.deletion


def backfill_video_gyms(apps, schema_editor):
    Video = apps.get_model('video_library', 'Video')
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    Group = apps.get_model('practice_planner', 'TrainingGroup')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None
    for video in Video.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else None
        if gym_id is None:
            candidates = set()
            ambiguous = False
            linked_users = [video.uploaded_by_id, video.primary_athlete_id]
            linked_users.extend(video.tagged_athletes.values_list('pk', flat=True))
            for user_id in linked_users:
                if user_id:
                    ids = list(Membership.objects.filter(
                        user_id=user_id, is_active=True, gym__is_active=True,
                    ).values_list('gym_id', flat=True).distinct()[:2])
                    if len(ids) == 1:
                        candidates.add(ids[0])
                    else:
                        ambiguous = True
            if video.training_group_id:
                group_gym = Group.objects.filter(pk=video.training_group_id).values_list('gym_id', flat=True).first()
                if group_gym:
                    candidates.add(group_gym)
            gym_id = next(iter(candidates)) if len(candidates) == 1 and not ambiguous else None
        if gym_id is not None:
            Video.objects.filter(pk=video.pk).update(gym_id=gym_id)


def backfill_technique_gyms(apps, schema_editor):
    Profile = apps.get_model('video_library', 'TechniqueProfile')
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None
    for profile in Profile.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else None
        if gym_id is None and profile.created_by_id:
            ids = list(Membership.objects.filter(
                user_id=profile.created_by_id, is_active=True, gym__is_active=True,
            ).values_list('gym_id', flat=True).distinct()[:2])
            gym_id = ids[0] if len(ids) == 1 else None
        if gym_id:
            Profile.objects.filter(pk=profile.pk).update(gym_id=gym_id)


class Migration(migrations.Migration):
    dependencies = [
        ('video_library', '0009_video_processing_error_alter_video_status'),
        ('gyms', '0001_initial'),
        ('practice_planner', '0004_group_template_gym'),
    ]
    operations = [
        migrations.AddField(
            model_name='techniqueprofile', name='gym',
            field=models.ForeignKey(
                to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
                related_name='technique_profiles', null=True, blank=True,
            ),
        ),
        migrations.AlterField(model_name='techniqueprofile', name='skill_name',
                              field=models.CharField(max_length=120)),
        migrations.AddConstraint(model_name='techniqueprofile', constraint=models.UniqueConstraint(
            fields=('gym', 'skill_name'), name='unique_technique_skill_per_gym')),
        migrations.AddField(
            model_name='video', name='gym',
            field=models.ForeignKey(
                to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
                related_name='library_videos', null=True, blank=True,
            ),
        ),
        migrations.RunPython(backfill_video_gyms, migrations.RunPython.noop),
        migrations.RunPython(backfill_technique_gyms, migrations.RunPython.noop),
    ]
