"""Original, concise coach review summaries; these are not scoring rules.

The 2021-2029 compulsory attachment contains replacement pages only.
The optional 2026-2030 attachment is a separate program from GymCan HP.
Keep the catalog stable: progress rows use the level/event/index as their key.
"""

EVENTS = (
    ('vault', 'Vault'),
    ('bars', 'Uneven Bars'),
    ('beam', 'Balance Beam'),
    ('floor', 'Floor Exercise'),
)

# Short assessment prompts, paraphrased from the supplied publications.
# Coaches must use the current complete rulebooks to assess official readiness.
CATALOG = {
    1: {
        'vault': ('Run, hurdle and stretch jump technique', 'Handstand shape and controlled flat-back landing'),
        'bars': ('Support and swing fundamentals', 'Body shape and controlled transition between bar positions'),
        'beam': ('Balance, posture and mount preparation', 'Controlled dance, acro preparation and dismount'),
        'floor': ('Basic tumbling shapes and directions', 'Dance, jumps and controlled finish'),
    },
    2: {
        'vault': ('Run and board contact with controlled body position', 'Handstand flat-back progression and landing'),
        'bars': ('Mount and pullover or support progression', 'Cast and swing sequence with dismount control'),
        'beam': ('Mount, travel and balance control', 'Dance, acro and dismount progression'),
        'floor': ('Connected basic tumbling elements', 'Dance passage, turn and landing control'),
    },
    3: {
        'vault': ('Approach, hurdle and board mechanics', 'Handstand entry, block preparation and landing'),
        'bars': ('Kip and cast progression', 'Circling, swing and dismount sequence'),
        'beam': ('Acro series preparation and balance', 'Leaps, turns and dismount'),
        'floor': ('Forward and backward tumbling preparation', 'Leap, turn and routine presentation'),
    },
    4: {
        'vault': ('Front handspring vault technique', 'Table contact, flight and controlled landing'),
        'bars': ('Kip, cast and circling elements', 'Bar change and compulsory dismount'),
        'beam': ('Compulsory acro and dance elements', 'Turn, connection and dismount'),
        'floor': ('Compulsory forward and backward acro', 'Dance elements, rhythm and presentation'),
    },
    5: {
        'vault': ('Front handspring vault technique', 'Flight, body position and landing'),
        'bars': ('Cast and circling elements in the compulsory routine', 'Transition and selected compulsory dismount'),
        'beam': ('Compulsory acro and leap sequence', 'Turn and dismount with control'),
        'floor': ('Compulsory acro passes', 'Dance passage, turns and artistry'),
    },
    6: {
        'vault': ('Eligible Level 6 vault selection', 'Approach, flight and controlled landing'),
        'bars': ('Level 6 value parts and special requirements', 'Circling or swing elements and dismount'),
        'beam': ('Level 6 acro and dance requirements', 'Turn, dismount and routine presentation'),
        'floor': ('Level 6 acro and dance requirements', 'Routine presentation and controlled landings'),
    },
    7: {
        'vault': ('Eligible Level 7 vault selection', 'Flight position and landing'),
        'bars': ('Level 7 value parts and special requirements', 'Bar changes, circling and dismount'),
        'beam': ('Level 7 acro series and dance requirements', 'Turn, dismount and presentation'),
        'floor': ('Level 7 acro passes and dance passage', 'Turns, presentation and landings'),
    },
    8: {
        'vault': ('Coach-verified Level 8 vault selection', 'Table contact, flight and landing'),
        'bars': ('Level 8 difficulty and special requirements', 'Element connections, bar use and dismount'),
        'beam': ('Level 8 acro series and dance requirements', 'Turns, composition and dismount'),
        'floor': ('Level 8 acro and dance requirements', 'Composition, artistry and landings'),
    },
    9: {
        'vault': ('Coach-verified Level 9 vault selection', 'Flight, dynamics and landing'),
        'bars': ('Level 9 difficulty and special requirements', 'Connections, composition and dismount'),
        'beam': ('Level 9 acro and dance requirements', 'Connections, composition and dismount'),
        'floor': ('Level 9 acro and dance requirements', 'Connections, composition and presentation'),
    },
    10: {
        'vault': ('Coach-verified Level 10 vault selection', 'Flight, dynamics and landing'),
        'bars': ('Level 10 difficulty and special requirements', 'Connections, composition and dismount'),
        'beam': ('Level 10 acro and dance requirements', 'Connections, composition and dismount'),
        'floor': ('Level 10 acro and dance requirements', 'Connections, composition and presentation'),
    },
}


def track_for(level):
    return 'compulsory' if level <= 5 else 'optional'


def items_for(level):
    return [
        {'code': f'{event}_{index}', 'event': event, 'event_name': name,
         'title': title, 'level': level}
        for event, name in EVENTS
        for index, title in enumerate(CATALOG[level][event], start=1)
    ]
