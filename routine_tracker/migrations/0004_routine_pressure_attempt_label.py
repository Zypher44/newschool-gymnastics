from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('routine_tracker', '0003_session_gym'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='dailyroutineattempt',
            name='unique_daily_routine_attempt',
        ),
        migrations.AddField(
            model_name='dailyroutineattempt',
            name='is_pressure',
            field=models.BooleanField(
                default=False,
                help_text='Whether this attempt was recorded in a pressure set.',
            ),
        ),
        migrations.AlterField(
            model_name='dailyroutineattempt',
            name='result',
            field=models.CharField(
                choices=[('wow', 'Wow'), ('hit', 'Hit'), ('missed', 'Attempt')],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name='dailyroutineattempt',
            constraint=models.UniqueConstraint(
                fields=('session', 'athlete', 'event', 'is_pressure', 'attempt_number'),
                name='unique_routine_attempt_context',
            ),
        ),
    ]
