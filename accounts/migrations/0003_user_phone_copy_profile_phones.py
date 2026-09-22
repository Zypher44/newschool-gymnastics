from django.db import migrations, models


def copy_profile_phone_numbers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    ParentProfile = apps.get_model('parents_portal', 'ParentProfile')
    CoachProfile = apps.get_model('coaches', 'CoachProfile')

    for profile in ParentProfile.objects.exclude(phone=''):
        User.objects.filter(
            pk=profile.user_id,
            phone='',
        ).update(phone=profile.phone)

    for profile in CoachProfile.objects.exclude(phone=''):
        User.objects.filter(
            pk=profile.user_id,
            phone='',
        ).update(phone=profile.phone)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_alter_user_role'),
        (
            'coaches',
            '0004_remove_coachathleteassignment_unique_coach_athlete_assignment_and_more',
        ),
        ('parents_portal', '0002_alter_parentathletelink_approved_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.RunPython(
            copy_profile_phone_numbers,
            migrations.RunPython.noop,
        ),
    ]
