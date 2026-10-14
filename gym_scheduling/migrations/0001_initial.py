from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('gyms', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='GroupSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekdays', models.JSONField(default=list)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='recurring_schedules', to='gyms.traininggroup')),
            ],
            options={
                'ordering': ['group__name', 'start_date', 'start_time'],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='schedule_dates_in_order'),
                    models.CheckConstraint(condition=models.Q(end_time__gt=models.F('start_time')), name='schedule_times_in_order'),
                ],
            },
        ),
    ]
