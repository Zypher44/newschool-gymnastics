from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('pathway', '0004_athleteroutineelement_vault_value')]

    operations = [
        migrations.AddField(
            model_name='pathwaylevel',
            name='program',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('hp', 'High Performance'),
                    ('usag_optional_2026', 'USAG Optional 2026–2030'),
                ],
                default='hp',
            ),
        ),
    ]
