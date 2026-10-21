from .passport_catalog import STAMPS
from .passport_badge_models import PassportBadgeDefinition


def badge_catalog(gym_id, include_archived=False, include_deleted=False):
    """Each gym starts with defaults; only an explicit coach save creates overrides."""
    catalog = {slot: {**definition, 'definition_version': 0, 'is_active': True,
                      'custom': False, 'requirement': definition['rule'], 'deleted': False}
               for slot, definition in STAMPS.items()}
    for badge in PassportBadgeDefinition.objects.filter(gym_id=gym_id):
        slot = badge.code + ':' + badge.variant
        definition = catalog.get(slot, {'slot': slot, 'code': badge.code, 'variant': badge.variant,
                                       'label': 'Personal achievement', 'metric': '', 'target': 0,
                                       'manual': True, 'custom': True, 'requirement': 'Coach confirms the achievement.'})
        catalog[slot] = {**definition, 'title': badge.title, 'name': badge.title,
                         'icon': badge.icon, 'rule': badge.description,
                         'definition_version': badge.version, 'is_active': badge.is_active and not badge.deleted_at,
                         'deleted': bool(badge.deleted_at)}
    return {slot: definition for slot, definition in catalog.items()
            if (include_archived or definition['is_active']) and (include_deleted or not definition['deleted'])}


def badge_choices(catalog):
    return [(slot, definition['title']) for slot, definition in catalog.items() if definition['is_active']]


def badge_snapshot(definition):
    return {key: definition[key] for key in ('slot', 'code', 'variant', 'icon', 'name', 'label', 'title',
                                             'rule', 'metric', 'target', 'manual', 'requirement', 'custom')}
