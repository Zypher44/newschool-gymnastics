from django.db import migrations, models
import django.db.models.deletion


def backfill_conversation_gyms(apps, schema_editor):
    Gym = apps.get_model('gyms', 'Gym')
    Membership = apps.get_model('gyms', 'GymMembership')
    Conversation = apps.get_model('communications', 'Conversation')
    only_gym = Gym.objects.first() if Gym.objects.count() == 1 else None
    for conversation in Conversation.objects.filter(gym__isnull=True).iterator():
        gym_id = only_gym.pk if only_gym else None
        if gym_id is None:
            participants = list(conversation.participants.values_list('pk', flat=True))
            user_ids = participants + ([conversation.related_athlete_id] if conversation.related_athlete_id else [])
            memberships = Membership.objects.filter(
                user_id__in=user_ids, is_active=True, gym__is_active=True,
            ).values_list('user_id', 'gym_id')
            by_user = {user_id: set() for user_id in user_ids}
            for user_id, gym in memberships:
                by_user[user_id].add(gym)
            if by_user:
                common = set.intersection(*by_user.values())
                gym_id = next(iter(common)) if len(common) == 1 else None
        if gym_id:
            Conversation.objects.filter(pk=conversation.pk).update(gym_id=gym_id)


class Migration(migrations.Migration):
    dependencies = [('communications', '0002_conversation_conversationparticipant_and_more'),
                    ('gyms', '0001_initial')]
    operations = [
        migrations.AddField(model_name='conversation', name='gym', field=models.ForeignKey(
            to='gyms.gym', on_delete=django.db.models.deletion.SET_NULL,
            related_name='conversations', null=True, blank=True)),
        migrations.RunPython(backfill_conversation_gyms, migrations.RunPython.noop),
    ]
