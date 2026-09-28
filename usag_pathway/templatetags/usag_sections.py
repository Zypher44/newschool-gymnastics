from django import template

from usag_pathway.catalog import items_for
from usag_pathway.xcel_catalog import DIVISIONS, items_for as xcel_items_for

register = template.Library()


@register.inclusion_tag('usag_pathway/sections.html')
def usag_sections():
    return {
        'sections': (
            {'title': 'USAG Optional 2026–2030', 'label': 'USAG Optional',
             'code': 'optional', 'levels': [
                 {'number': level, 'count': len(items_for(level))}
                 for level in range(6, 11)
             ]},
            {'title': 'USAG Compulsory Levels 1–5', 'label': 'USAG Compulsory',
             'code': 'compulsory', 'levels': [
                 {'number': level, 'count': len(items_for(level))}
                 for level in range(1, 6)
             ]},
        )
    }


@register.inclusion_tag('usag_pathway/xcel_sections.html')
def xcel_sections():
    return {
        'divisions': [
            {'code': division, 'name': division.title(),
             'count': len(xcel_items_for(division))}
            for division in DIVISIONS
        ],
    }
