from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('practice_focus', '0002_individual_plans'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gyms', '__first__'),
    ]
    operations = [migrations.CreateModel(
        name='CoachReportPreference',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('show_group_averages', models.BooleanField(default=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('coach', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gyms.gym')),
        ],
        options={'constraints': [models.UniqueConstraint(fields=('gym', 'coach'), name='unique_coach_report_preference')]},
    )]
