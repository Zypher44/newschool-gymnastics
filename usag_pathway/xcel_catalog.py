"""Concise, original coach prompts based on the supplied 2022-2026 Xcel pages.

Those pages omit the vault chart. This catalog is
not a current rulebook and must never be used to calculate an official score.
"""

from .catalog import EVENTS

DIVISIONS = ('bronze', 'silver', 'gold', 'platinum', 'diamond')

XCEL_CATALOG = {
    'bronze': {
        'vault': ('Check the selected vault against the current Bronze vault chart',),
        'bars': ('Low-bar mount', 'Cast with the hips off the bar', 'Circling skill', 'Low-bar dismount without a salto'),
        'beam': ('Half turn on one or two feet', 'Jump or leap within the routine', 'Non-flight acro skill', 'Dismount without a salto or aerial'),
        'floor': ('Connected acro elements', 'A second acro pass', 'Dance passage with a split leap', 'Half turn on one foot'),
    },
    'silver': {
        'vault': ('Check the selected vault against the current Silver vault chart',),
        'bars': ('Mount', 'Cast reaching the division angle', 'Circling skill', 'Permitted dismount without a salto'),
        'beam': ('Half turn on one foot', 'Jump or leap meeting the division split', 'Non-flight acro skill', 'Dismount'),
        'floor': ('Connected acro elements including flight', 'A second acro pass', 'Dance passage meeting the division split', 'Full turn on one foot'),
    },
    'gold': {
        'vault': ('Check the selected vault against the current Gold vault chart',),
        'bars': ('Clear-support skill reaching the division angle', 'First circling skill', 'Second circling skill', 'High-bar dismount'),
        'beam': ('Full turn on one foot', 'Two dance elements including the required split', 'Two acro elements, one through vertical', 'Dismount'),
        'floor': ('Connected acro flight elements', 'A second acro pass or aerial/salto', 'Dance passage meeting the division split', 'Full turn on one foot'),
    },
    'platinum': {
        'vault': ('Check the selected vault against the current Platinum vault chart',),
        'bars': ('Clear-support skill above horizontal', 'Circling skill', 'Kip', 'High-bar dismount meeting the division value'),
        'beam': ('Full turn on one foot', 'Dance series and split element', 'Acro flight or series through vertical', 'Dismount'),
        'floor': ('Connected acro flight and salto', 'Second acro pass', 'Dance passage meeting the division split', 'Full turn on one foot'),
    },
    'diamond': {
        'vault': ('Check the selected vault against the current Diamond vault chart',),
        'bars': ('Clear-support skill reaching the division angle', 'Circling skill at the required difficulty', 'Additional release, turn or circling skill', 'High-bar dismount at the required difficulty'),
        'beam': ('Full turn on one foot', 'Dance series and split element', 'Acro series and a flight element', 'Salto or aerial dismount'),
        'floor': ('Two distinct connected acro flight passes', 'Two different saltos at the required difficulty', 'Dance passage meeting the division split', 'Turn at the required difficulty'),
    },
}


def items_for(division):
    return [
        {'code': f'{event}_{index}', 'event': event, 'event_name': name,
         'title': title}
        for event, name in EVENTS
        for index, title in enumerate(
            XCEL_CATALOG[division].get(event, ()), start=1,
        )
    ]
