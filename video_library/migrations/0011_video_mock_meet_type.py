from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('video_library', '0010_video_gym'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='video_type',
            field=models.CharField(
                choices=[
                    ('practice', 'Practice'),
                    ('competition', 'Competition'),
                    ('testing', 'Performance Testing'),
                    ('drill', 'Drill'),
                    ('routine', 'Routine'),
                    ('mock_meet', 'Mock Meet'),
                    ('progress', 'Progress Video'),
                    ('other', 'Other'),
                ],
                default='practice',
                max_length=30,
            ),
        ),
    ]
