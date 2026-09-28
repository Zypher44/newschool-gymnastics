from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('coaches', '0004_remove_coachathleteassignment_unique_coach_athlete_assignment_and_more')]

    operations = [
        migrations.AddField(
            model_name='teamevent', name='audience',
            field=models.CharField(max_length=12, choices=[
                ('all', 'Everyone in the gym'), ('coaches', 'Coaches'),
                ('parents', 'Parents'), ('group', 'Training group'),
            ], default='all'),
        ),
        migrations.AddField(
            model_name='teamevent', name='training_group',
            field=models.ForeignKey(to='gyms.traininggroup', on_delete=django.db.models.deletion.SET_NULL,
                                    null=True, blank=True, related_name='team_events'),
        ),
    ]
