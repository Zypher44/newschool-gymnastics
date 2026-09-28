from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('usag_pathway', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='XcelRequirementProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('division', models.CharField(max_length=20)),
                ('event', models.CharField(max_length=10)),
                ('requirement_code', models.CharField(max_length=30)),
                ('status', models.CharField(choices=[('not_started', 'Not started'), ('developing', 'Developing'), ('achieved', 'Achieved'), ('ready', 'Coach reviewed')], default='not_started', max_length=15)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='xcel_requirement_progress', to=settings.AUTH_USER_MODEL)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gyms.gym')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='xcelrequirementprogress',
            constraint=models.UniqueConstraint(fields=('gym', 'athlete', 'division', 'requirement_code'), name='unique_gym_xcel_requirement_progress'),
        ),
    ]
