"""Restore the existing HP catalogue on fresh installations.

The frozen UTF-8 seed comes from the HP data already present in this project.
Existing levels and requirements are retained without overwriting gym progress.
"""
import json
from pathlib import Path

from django.db import migrations


def seed_hp(apps, schema_editor):
    Level = apps.get_model('pathway', 'PathwayLevel')
    Event = apps.get_model('pathway', 'PathwayEvent')
    Requirement = apps.get_model('pathway', 'PathwayRequirement')
    db = schema_editor.connection.alias
    data = json.loads(Path(__file__).with_name('hp_seed.json').read_text(encoding='utf-8'))
    for fields in data['levels']:
        Level.objects.using(db).get_or_create(
            code=fields['code'], defaults={**fields, 'program': 'hp'},
        )
    for fields in data['requirements']:
        level = Level.objects.using(db).get(code=fields['level_code'])
        event = Event.objects.using(db).get(code=fields['event_code'])
        key = {
            'level': level, 'event': event, 'title': fields['title'],
            'display_order': fields['display_order'],
        }
        Requirement.objects.using(db).get_or_create(
            **key,
            defaults={k: v for k, v in fields.items()
                      if k not in ('level_code', 'event_code', 'title', 'display_order')},
        )


class Migration(migrations.Migration):
    dependencies = [('pathway', '0006_seed_usag_optional_levels')]
    operations = [migrations.RunPython(seed_hp, migrations.RunPython.noop)]
