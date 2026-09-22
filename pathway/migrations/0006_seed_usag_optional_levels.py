"""Frozen, paraphrased checklist data from the supplied 2026–2030 USAG PDF.

Sources use the book's printed section/page numbers. This is a coach-assessed
requirements summary, not an exhaustive code, scoring engine or Ontario rule set.
Do not replace this frozen data with imports from changing application modules.
"""
from django.db import migrations


PROGRAM = 'usag_optional_2026'
SOURCE = 'USAG 2026–2030 Optional Code of Points'
NOTICE = (
    'Coach-assessed USAG requirements summary, effective August 1, 2026–July 31, 2030. '
    'Not an Ontario/CCP or HP rule set. Completion records checklist progress, '
    'not competition eligibility or an official score. The supplied copy omits '
    'the floor element catalogue and vault-value appendices; coaches must verify '
    'the full current code and applicable competition rules.'
)

# Each tuple is one requirement, including its permitted alternatives.
# Alternative skills are intentionally not separate required checklist items.
BARS = {
    6: [
        ('Cast amplitude', 'Develop a cast to at least 45° above horizontal. Special-requirement credit is possible above horizontal, with applicable angle deductions below the target.'),
        ('Bar change', 'Perform at least one bar change with credited elements on both bars. Simply climbing onto a bar does not establish this requirement.'),
        ('Clear circling element', 'Perform a 360° clear circle from Group 3, 6 or 7; verify clear support and the applicable technique for recognition.'),
        ('Salto dismount', 'Perform a credited salto dismount rated A or higher within the allowed difficulty.'),
    ],
    7: [
        ('Cast to handstand', 'Develop a cast to handstand. The special requirement can receive credit from 45° above horizontal, but handstand-angle deductions still apply.'),
        ('B clear circle', 'Include a credited 360° clear circling element rated at least B.'),
        ('Group 3, 6 or 7 circle', 'Include a second 360° clear circling element; at least one of the two must be from Group 3, 6 or 7. The circles may be the same or different, subject to repetition-credit rules.'),
        ('Salto dismount', 'Perform a credited salto dismount rated A or higher within the allowed difficulty.'),
    ],
    8: [
        ('Cast to handstand', 'Include a credited cast to handstand, applying the code’s recognition and angle criteria.'),
        ('B flight or turn', 'Include a B-or-higher flight element other than the dismount, OR a qualifying B-or-higher element with at least a half turn other than the mount or dismount.'),
        ('B clear circle', 'Include a second B element: a 360° clear circle from Group 3, 6 or 7, excluding the dismount. Verify that two elements satisfy the pair of requirements.'),
        ('Salto dismount', 'Perform a credited salto dismount rated A or higher within the allowed difficulty.'),
    ],
    9: [
        ('Two bar changes', 'Include at least two bar changes, with credited elements establishing work on both bars.'),
        ('B flight element', 'Include a credited flight element rated at least B, excluding the dismount.'),
        ('Second flight or turn', 'Use a different element from the preceding flight requirement: a C-or-higher flight element excluding the dismount, OR a B-or-higher element with at least a half turn excluding mount and dismount.'),
        ('B salto dismount', 'Perform a credited salto dismount rated B or higher within the allowed difficulty.'),
    ],
    10: [
        ('C flight element', 'Include a credited flight element rated at least C, excluding the dismount.'),
        ('Second B flight element', 'Include a second, different credited flight element rated at least B, excluding the dismount.'),
        ('C turning element', 'Include a credited long-axis turning element rated at least C, excluding mount and dismount.'),
        ('C salto dismount', 'Perform a credited salto dismount rated C or higher.'),
    ],
}

BEAM_ACRO = {
    6: 'Perform a qualifying non-flight acro series OR one acro flight element. The series excludes mount/dismount and must include an element passing through inverted vertical in handstand support. The chosen elements must start and finish on the beam.',
    7: 'Perform a qualifying acro series AND an acro flight element. The flight may be in the series or separate. The series excludes mount/dismount and includes an element passing through inverted vertical in handstand support.',
    8: 'Perform a two-element acro series with at least one flight element, excluding mount and dismount. Confirm direct connection and element recognition.',
    9: 'Perform an acro series of at least two directly connected flight elements, excluding mount and dismount.',
    10: 'Perform at least two directly connected acro flight elements, including at least one C flight element, OR directly connect an A non-flight Group 7 acro element to an E acro flight element. Mount and dismount are excluded.',
}

FLOOR = {
    6: [
        ('First salto pass', 'Perform an acro pass with at least two directly connected flight elements, including a credited salto.'),
        ('Different second salto', 'Perform a second pass with at least two directly connected flight elements including a different salto, OR perform an isolated B salto different from the first pass’s salto.'),
        ('Dance passage', 'Connect at least two different Group 1 dance elements directly or indirectly, including a leap requiring a 180° cross or side split. Apply recognition and split-angle criteria.'),
        ('Full turn', 'Perform a credited turn of at least 360° on one foot.'),
    ],
    7: [
        ('Backward salto pass', 'Perform a pass of at least two directly connected flight elements, including a backward salto. There must be at least two acro passes in the routine.'),
        ('Forward pass and stretched salto', 'Perform a separate pass containing a forward salto. Across the forward/backward passes, at least one salto must be stretched, without twist, and land on two feet.'),
        ('Dance passage', 'Connect at least two different Group 1 dance elements directly or indirectly, including a leap requiring a 180° cross or side split. Apply recognition and split-angle criteria.'),
        ('Full turn', 'Perform a credited turn of at least 360° on one foot.'),
    ],
}

VP = {6: '4 A + 2 B', 7: '4 A + 3 B', 8: '4 A + 4 B',
      9: '3 A + 4 B + 1 C', 10: '3 A + 3 B + 2 C'}

RESTRICTIONS = {
    'bars': {
        6: 'Check A/B choices, the allowance for only one selected C clear-hip/Stalder/pike-sole circle to handstand, and the prohibition on flight transfers between bars. Other C and all D/E elements are restricted. Allowed C elements receive B credit.',
        7: 'Check A/B choices and the listed C exceptions for handstand casts/circles and half turns. Other C and all D/E elements are restricted. Allowed C elements receive B credit.',
        8: 'Check A/B choices, the listed C exceptions and the allowance for one other C element in chronological order. Further restricted C and all D/E elements are restricted. Credited C elements receive B credit.',
        9: 'Check A/B/C choices, the listed D/E turning exceptions and the allowance for one other D/E element in chronological order. Further restricted D/E elements are restricted. Credited D/E elements receive C credit.',
        10: 'There is no level-specific difficulty cap. Confirm recognition, repetition, connection and bonus rules; planned difficulty alone does not establish credited difficulty.',
    },
    'beam_floor': {
        6: 'Check A/B elements and the allowance for one C dance element in chronological order. Additional C dance and all C/D/E acro and D/E dance elements are restricted. The allowed C dance receives B credit.',
        7: 'Check A/B elements and allowed C dance elements. C/D/E acro and D/E dance elements are restricted. Allowed C dance elements receive B credit.',
        8: 'Check A/B elements, C dance elements and the allowance for one C acro element in chronological order. Further C acro and D/E acro/dance elements are restricted. Credited C elements receive B credit.',
        9: 'Check A/B/C elements, D/E dance elements and the allowance for one D/E acro element in chronological order. Further D/E acro elements are restricted. Credited D/E elements receive C credit.',
        10: 'There is no level-specific difficulty cap. Confirm recognition, repetition, connection and bonus rules; planned difficulty alone does not establish credited difficulty.',
    },
}


def seed_levels(apps, schema_editor):
    Level = apps.get_model('pathway', 'PathwayLevel')
    Event = apps.get_model('pathway', 'PathwayEvent')
    Requirement = apps.get_model('pathway', 'PathwayRequirement')
    db = schema_editor.connection.alias
    events = {}
    for order, (code, name) in enumerate([
        ('vault', 'Vault'), ('bars', 'Uneven Bars'),
        ('beam', 'Beam'), ('floor', 'Floor'),
    ], 1):
        events[code], _ = Event.objects.using(db).get_or_create(
            code=code, defaults={'name': name, 'order': order},
        )

    for number in range(6, 11):
        level, _ = Level.objects.using(db).get_or_create(
            code=f'usag_2026_level_{number}',
            defaults={
                'name': f'USAG Level {number}', 'program': PROGRAM,
                'order': number, 'description': NOTICE, 'is_active': True,
            },
        )

        def add(event, title, description, source, order, kind='routine', required=True):
            # Never delete/recreate requirements: athlete progress references their IDs.
            Requirement.objects.using(db).get_or_create(
                level_id=level.pk, event_id=events[event].pk, title=title,
                defaults={
                    'description': f'{description}\n\nSource: {SOURCE}, {source}.',
                    'requirement_type': kind, 'display_order': order,
                    'is_required': required, 'is_active': True,
                    'notes': 'Paraphrased checklist. Coach verification required; not an official score.',
                },
            )

        if number in (6, 7):
            vault = (
                'Choose ONE permitted entry: front handspring, Tsukahara or round-off/Yurchenko '
                'entry over the table onto the specified mat stack. Landing is on the feet; '
                + ('Level 7 also permits the prescribed back landing for the Tsukahara/Yurchenko options. ' if number == 7 else '')
                + 'The coach must verify the setup and entry/landing technique. No flipping is allowed '
                'in the vault or after the feet contact the stack. These are alternatives, not three required vaults.'
            )
        else:
            vault = (
                f'Coach must confirm the selected vault is permitted at Level {number}, '
                'its official value and the required apparatus setup using the current vault appendix. '
                'That appendix is missing from the supplied PDF; no vault values or individual '
                'vault options are asserted by this checklist.'
            )
        add('vault', 'Coach verification of selected vault', vault, 'Vault–1–7', 1, 'vault')

        for i, (title, description) in enumerate(BARS[number], 1):
            add('bars', title, description, 'Bars–22–29', i, 'cr')

        beam = [
            ('Acro requirement', BEAM_ACRO[number]),
            ('Split leap or jump', 'Perform a credited leap or jump requiring a 180° cross or side split. Verify the minimum separation for recognition and any insufficient-split deduction; the target and the credit threshold are not identical.'),
            ('Full turn', 'Perform a credited Group 3 turn of at least 360° on one foot.'),
            ('Aerial or salto dismount', (
                'Perform a credited C-or-higher dismount, OR a B dismount directly connected to an acro series containing at least C acro, or to a C-or-higher acro flight/dance element.'
                if number == 10 else
                f'Perform a credited aerial or salto dismount rated at least {"B" if number == 9 else "A"}, within the level’s difficulty restrictions.'
            )),
        ]
        for i, (title, description) in enumerate(beam, 1):
            add('beam', title, description, 'Beam–16–22', i, 'cr')

        floor = FLOOR.get(number) or [
            ('Two-salto pass', 'Include an acro pass with at least two saltos, the same or different, connected directly or indirectly through flight elements. Verify connection and value-part recognition.'),
            ('Three different saltos', 'Include three different credited saltos in the routine. Aerials do not count as saltos for this requirement.'),
            ('Dance passage', 'Connect at least two different Group 1 dance elements directly or indirectly, including a leap requiring a 180° cross or side split. Apply recognition and split-angle criteria.'),
            ('Last acro pass', f'The last acro pass initiated must contain a credited salto rated at least { {8: "A", 9: "B", 10: "C"}[number] }. Apply repetition and connection rules; merely planning the salto is insufficient.'),
        ]
        for i, (title, description) in enumerate(floor, 1):
            add('floor', title, description, 'Floor–14–23', i, 'cr')

        for event in ('bars', 'beam', 'floor'):
            add(event, 'Value-part coverage',
                f'Confirm {VP[number]} credited value parts. Permitted higher values may replace lower values one-for-one. Apply level-specific credited values and repetition rules; a skill list alone is insufficient.',
                'General–17–19, General–27', 10, 'dv')
            restrictions = RESTRICTIONS['bars' if event == 'bars' else 'beam_floor'][number]
            add(event, 'Allowed difficulty and recognition review', restrictions,
                {'bars': 'Bars–22–29', 'beam': 'Beam–22', 'floor': 'Floor–24'}[event], 11)
            if number >= 8:
                credit = '0.30' if number == 10 else '0.20'
                add(event, 'Composition credit review',
                    f'Coach may assess up to {credit} composition credit using the event-specific criteria. This is additional start-value credit, not a mandatory skill checklist item or an automatic award.',
                    {'bars': 'Bars–50', 'beam': 'Beam–39', 'floor': 'Floor–39'}[event],
                    20, 'other', False)
            if number >= 9:
                add(event, 'Bonus planning review',
                    'Coach may review eligible connection and difficulty bonuses, their limits and the effects of falls/repetition. No bonus is calculated or guaranteed by checking this item. Optional bonuses do not enter the required-progress denominator.',
                    'General–25–26 and the event’s Bonus chapter', 21, 'bonus', False)


class Migration(migrations.Migration):
    dependencies = [('pathway', '0005_pathwaylevel_program')]
    # Reversing must not destroy coach assessments or assignments referencing this data.
    operations = [migrations.RunPython(seed_levels, migrations.RunPython.noop)]
