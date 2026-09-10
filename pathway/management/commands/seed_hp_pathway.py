from django.core.management.base import BaseCommand

from pathway.models import (
    PathwayEvent,
    PathwayLevel,
    PathwayRequirement,
)


class Command(BaseCommand):

    help = (
        'Cleanly rebuild the GymCan National '
        'and High Performance pathway.'
    )


    def handle(
        self,
        *args,
        **options,
    ):

        # ========================================================
        # LEVELS
        # ========================================================

        levels = [
            {
                'name': 'Aspire',
                'code': 'aspire',
                'order': 1,
                'minimum_age': 9,
                'maximum_age': 11,
                'description': (
                    'Pre-Youth pathway stage.'
                ),
            },
            {
                'name': 'Youth 1',
                'code': 'youth_1',
                'order': 2,
                'minimum_age': 10,
                'maximum_age': 14,
                'description': (
                    'Novice 1st Year.'
                ),
            },
            {
                'name': 'Youth 2',
                'code': 'youth_2',
                'order': 3,
                'minimum_age': 11,
                'maximum_age': 14,
                'description': (
                    'Novice 2nd Year.'
                ),
            },
            {
                'name': 'Novice / Youth 3',
                'code': 'youth_3',
                'order': 4,
                'minimum_age': 11,
                'maximum_age': 14,
                'description': (
                    'Novice 3rd Year / Pre-Junior.'
                ),
            },
        ]


        level_objects = {}


        for level_data in levels:

            level, created = (
                PathwayLevel.objects.update_or_create(
                    code=level_data['code'],
                    defaults=level_data,
                )
            )

            level_objects[
                level_data['code']
            ] = level

            self.stdout.write(
                self.style.SUCCESS(
                    f'Level ready: {level.name}'
                )
            )


        # ========================================================
        # EVENTS
        # ========================================================

        events = [
            {
                'code': (
                    PathwayEvent.EVENT_VAULT
                ),
                'name': 'Vault',
                'order': 1,
            },
            {
                'code': (
                    PathwayEvent.EVENT_BARS
                ),
                'name': 'Uneven Bars',
                'order': 2,
            },
            {
                'code': (
                    PathwayEvent.EVENT_BEAM
                ),
                'name': 'Beam',
                'order': 3,
            },
            {
                'code': (
                    PathwayEvent.EVENT_FLOOR
                ),
                'name': 'Floor',
                'order': 4,
            },
        ]


        event_objects = {}


        for event_data in events:

            event, created = (
                PathwayEvent.objects.update_or_create(
                    code=event_data['code'],
                    defaults=event_data,
                )
            )

            event_objects[
                event_data['code']
            ] = event

            self.stdout.write(
                self.style.SUCCESS(
                    f'Event ready: {event.name}'
                )
            )


        # ========================================================
        # CLEAN REBUILD
        # ========================================================
        #
        # During development we completely remove the official
        # seeded requirements for these four pathway levels.
        #
        # This guarantees:
        #
        # - no old titles remain
        # - no capitalization duplicates remain
        # - no obsolete bonus cards remain
        # - no duplicate Vault cards remain
        #
        # IMPORTANT:
        # AthletePathwayRequirement records pointing to these
        # requirements will also be removed through CASCADE.
        #
        # Before production we will replace this approach with
        # stable requirement identifiers.
        # ========================================================

        PathwayRequirement.objects.filter(
            level__code__in=[
                'aspire',
                'youth_1',
                'youth_2',
                'youth_3',
            ],
            event__code__in=[
                'vault',
                'bars',
                'beam',
                'floor',
            ],
        ).delete()


        self.stdout.write(
            self.style.WARNING(
                (
                    'Existing seeded pathway requirements '
                    'were cleared for clean rebuild.'
                )
            )
        )


        # ========================================================
        # HELPER
        # ========================================================

        def add_requirement(
            level_code,
            event_code,
            title,
            requirement_type,
            display_order,
            description='',
            requirement_number=None,
            value=None,
            bonus_value=None,
            is_required=True,
            notes='',
        ):

            return (
                PathwayRequirement.objects.create(
                    level=level_objects[
                        level_code
                    ],

                    event=event_objects[
                        event_code
                    ],

                    title=title,

                    requirement_type=(
                        requirement_type
                    ),

                    description=(
                        description
                    ),

                    requirement_number=(
                        requirement_number
                    ),

                    value=value,

                    bonus_value=(
                        bonus_value
                    ),

                    is_required=(
                        is_required
                    ),

                    display_order=(
                        display_order
                    ),

                    notes=notes,

                    is_active=True,
                )
            )


        # ========================================================
        # VAULT — ASPIRE
        # ========================================================

        add_requirement(
            'aspire',
            'vault',
            'Timer Tsukahara to Feet',
            PathwayRequirement.TYPE_VAULT,
            1,
            value=3.0,
        )


        add_requirement(
            'aspire',
            'vault',
            'Timer Tsukahara to Candle',
            PathwayRequirement.TYPE_VAULT,
            2,
            value=3.5,
        )


        add_requirement(
            'aspire',
            'vault',
            'Timer Yurchenko to Feet',
            PathwayRequirement.TYPE_VAULT,
            3,
            value=3.0,
        )


        add_requirement(
            'aspire',
            'vault',
            'Timer Yurchenko to Candle',
            PathwayRequirement.TYPE_VAULT,
            4,
            value=3.5,
        )


        add_requirement(
            'aspire',
            'vault',
            'Timer Handspring to Back',
            PathwayRequirement.TYPE_VAULT,
            5,
            value=3.0,
        )


        add_requirement(
            'aspire',
            'vault',
            'Timer Handspring to Feet',
            PathwayRequirement.TYPE_VAULT,
            6,
            value=3.5,
        )


        add_requirement(
            'aspire',
            'vault',
            'Tsukahara Tuck',
            PathwayRequirement.TYPE_VAULT,
            7,
            value=4.5,
        )


        add_requirement(
            'aspire',
            'vault',
            'Yurchenko Tuck',
            PathwayRequirement.TYPE_VAULT,
            8,
            value=4.5,
        )


        # ========================================================
        # VAULT — YOUTH 1 / YOUTH 2 / YOUTH 3
        # ========================================================

        for level_code in [
            'youth_1',
            'youth_2',
            'youth_3',
        ]:

            add_requirement(
                level_code,
                'vault',
                'Competition Vault',
                PathwayRequirement.TYPE_VAULT,
                1,
                description=(
                    'Athlete is working toward '
                    'a vault listed in the '
                    'WG Code of Points.'
                ),
            )


            add_requirement(
                level_code,
                'vault',
                'Salto Vault Bonus',
                PathwayRequirement.TYPE_BONUS,
                20,
                description=(
                    'Bonus for salto vaults.'
                ),
                bonus_value=0.2,
                is_required=False,
            )


        # ========================================================
        # BARS — ASPIRE
        # ========================================================

        bars_aspire = [
            (
                1,
                (
                    'Close Bar Circle '
                    'Element to 30°'
                ),
                (
                    '+0.3 bonus if completed '
                    'in handstand within 10°.'
                ),
            ),
            (
                2,
                (
                    'Second Close Bar Circle '
                    'Element to 30°'
                ),
                (
                    '+0.3 bonus if completed '
                    'in handstand.'
                ),
            ),
            (
                3,
                (
                    'Glide Kip or Long Kip '
                    'to Cast Handstand to 30°'
                ),
                (
                    '+0.2 bonus if completed '
                    'in handstand, awarded once.'
                ),
            ),
            (
                4,
                'Back Giant',
                (
                    '+0.5 if both back and '
                    'front giants are performed.'
                ),
            ),
            (
                5,
                'Dismount',
                (
                    '+0.1 bonus for '
                    'salto dismount.'
                ),
            ),
        ]


        for (
            number,
            title,
            description,
        ) in bars_aspire:

            add_requirement(
                'aspire',
                'bars',
                title,
                PathwayRequirement.TYPE_CR,
                number,
                description=description,
                requirement_number=number,
                value=0.5,
            )


        add_requirement(
            'aspire',
            'bars',
            (
                'Connected Close '
                'Bar Circles Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus each time close bar circles '
                'are directly connected within 30°.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        # ========================================================
        # BARS — YOUTH 1
        # ========================================================

        bars_youth_1 = [
            (
                1,
                (
                    'Close Bar Circle '
                    'Element to 30°'
                ),
                (
                    '+0.2 bonus if completed '
                    'in handstand.'
                ),
            ),
            (
                2,
                (
                    'Second Close Bar Circle '
                    'Element to 30° '
                    'with Different Root'
                ),
                (
                    '+0.2 bonus if completed '
                    'in handstand.'
                ),
            ),
            (
                3,
                (
                    'Cast to Handstand '
                    'to 30°'
                ),
                (
                    '+0.1 bonus if completed '
                    'in handstand, awarded once.'
                ),
            ),
            (
                4,
                (
                    'Forward Giant or '
                    'Backward Giant'
                ),
                (
                    'Athlete must perform at least '
                    'one giant, forward or backward.'
                ),
            ),
        ]


        for (
            number,
            title,
            description,
        ) in bars_youth_1:

            add_requirement(
                'youth_1',
                'bars',
                title,
                PathwayRequirement.TYPE_CR,
                number,
                description=description,
                requirement_number=number,
                value=0.5,
            )


        add_requirement(
            'youth_1',
            'bars',
            (
                'Forward + Backward '
                'Giant Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus awarded when the athlete '
                'performs both a forward giant '
                'and a backward giant.'
            ),
            bonus_value=0.5,
            is_required=False,
        )


        add_requirement(
            'youth_1',
            'bars',
            (
                'Connected Close Bar '
                'Circles Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            21,
            description=(
                'Bonus each time close bar circles '
                'are directly connected within 30°.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        add_requirement(
            'youth_1',
            'bars',
            'Salto Dismount Bonus',
            PathwayRequirement.TYPE_BONUS,
            22,
            description=(
                'Bonus for a salto dismount.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        add_requirement(
            'youth_1',
            'bars',
            'Double Salto Dismount Bonus',
            PathwayRequirement.TYPE_BONUS,
            23,
            description=(
                'Bonus for a double '
                'salto dismount.'
            ),
            bonus_value=0.3,
            is_required=False,
        )


        # ========================================================
        # BARS — YOUTH 2
        # ========================================================

        bars_youth_2 = [
            (
                1,
                'Flight Element',
                (
                    'HB-LB, LB-HB, '
                    'or same-bar flight.'
                ),
            ),
            (
                2,
                (
                    'Non-Flight Element '
                    'with 360° Turn'
                ),
                '',
            ),
            (
                3,
                (
                    'Close Bar Circle '
                    'to Handstand'
                ),
                '',
            ),
            (
                4,
                (
                    'Second Close Bar Circle '
                    'to 30° with Different Root'
                ),
                (
                    '+0.1 bonus if completed '
                    'in handstand.'
                ),
            ),
            (
                5,
                'Cast to Handstand',
                '',
            ),
            (
                6,
                (
                    'Forward Giant or '
                    'Backward Giant'
                ),
                (
                    'Athlete must perform at least '
                    'one giant, forward or backward.'
                ),
            ),
        ]


        for (
            number,
            title,
            description,
        ) in bars_youth_2:

            add_requirement(
                'youth_2',
                'bars',
                title,
                PathwayRequirement.TYPE_CR,
                number,
                description=description,
                requirement_number=number,
                value=0.5,
            )


        add_requirement(
            'youth_2',
            'bars',
            (
                'Forward + Backward '
                'Giant Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus awarded when the athlete '
                'performs both a forward giant '
                'and a backward giant.'
            ),
            bonus_value=0.5,
            is_required=False,
        )


        add_requirement(
            'youth_2',
            'bars',
            'Salto Dismount Bonus',
            PathwayRequirement.TYPE_BONUS,
            21,
            description=(
                'Bonus for a salto dismount.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        add_requirement(
            'youth_2',
            'bars',
            (
                'Double Salto '
                'Dismount Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            22,
            description=(
                'Bonus for a double '
                'salto dismount.'
            ),
            bonus_value=0.3,
            is_required=False,
        )


        # ========================================================
        # BARS — NOVICE / YOUTH 3
        # ========================================================

        bars_youth_3 = [
            (
                1,
                (
                    'Flight Element '
                    'High Bar to Low Bar'
                ),
            ),
            (
                2,
                (
                    'Flight Element '
                    'Low Bar to High Bar'
                ),
            ),
            (
                3,
                (
                    'Same-Bar '
                    'Flight Element'
                ),
            ),
            (
                4,
                'Different Grip',
            ),
            (
                5,
                (
                    'Non-Flight Element '
                    'with 360° Turn'
                ),
            ),
            (
                6,
                (
                    'Close Bar Circle '
                    'to Handstand'
                ),
            ),
        ]


        for (
            number,
            title,
        ) in bars_youth_3:

            add_requirement(
                'youth_3',
                'bars',
                title,
                PathwayRequirement.TYPE_CR,
                number,
                requirement_number=number,
                value=0.5,
            )


        add_requirement(
            'youth_3',
            'bars',
            'Salto Dismount Bonus',
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus for a salto dismount.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        add_requirement(
            'youth_3',
            'bars',
            (
                'Double Salto '
                'Dismount Bonus'
            ),
            PathwayRequirement.TYPE_BONUS,
            21,
            description=(
                'Bonus for a double '
                'salto dismount.'
            ),
            bonus_value=0.2,
            is_required=False,
        )


        add_requirement(
            'youth_3',
            'bars',
            'Complete All 6 CR Bonus',
            PathwayRequirement.TYPE_BONUS,
            22,
            description=(
                'Bonus awarded when all six '
                'composition requirements '
                'are performed.'
            ),
            bonus_value=0.5,
            is_required=False,
        )


        # ========================================================
        # BEAM — CORE REQUIREMENTS
        # ========================================================

        beam_requirements = {

            'aspire': [
                (
                    1,
                    (
                        'Press to Handstand Mount '
                        'or B Mount'
                    ),
                    '',
                ),
                (
                    2,
                    'Minimum 1/1 Pirouette',
                    '',
                ),
                (
                    3,
                    (
                        'Acro Series with Second '
                        'Element Being Flight'
                    ),
                    (
                        '+0.3 bonus if the series '
                        'contains two flight elements.'
                    ),
                ),
                (
                    4,
                    'Acro Showing Flexibility',
                    '',
                ),
                (
                    5,
                    (
                        'Dance Connection with Split '
                        'Leap and Split/Straddle Jump'
                    ),
                    '',
                ),
            ],

            'youth_1': [
                (
                    1,
                    (
                        'Connection of 2 Different '
                        'Dance Elements with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    'Minimum 1/1 Pirouette',
                    '',
                ),
                (
                    3,
                    (
                        'Acro Series with Minimum '
                        '1 Flight Element'
                    ),
                    '',
                ),
                (
                    4,
                    (
                        'Acro in Different Directions '
                        '(Backward + Forward/Sideward)'
                    ),
                    '',
                ),
            ],

            'youth_2': [
                (
                    1,
                    (
                        'Connection of 2 Different '
                        'Dance Elements with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    'Minimum 1/1 Pirouette',
                    '',
                ),
                (
                    3,
                    (
                        'Acro Series with Minimum '
                        '2 Flight Elements'
                    ),
                    (
                        '+0.1 bonus if the series '
                        'includes a salto.'
                    ),
                ),
                (
                    4,
                    (
                        'Acro in Different Directions '
                        '(Backward + Forward/Sideward)'
                    ),
                    '',
                ),
            ],

            'youth_3': [
                (
                    1,
                    (
                        'Connection of 2 Different '
                        'Dance Elements with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    'Minimum 1/1 Pirouette',
                    '',
                ),
                (
                    3,
                    (
                        'Acro Series with Minimum '
                        '2 Flight Elements'
                    ),
                    (
                        '+0.2 bonus if the series '
                        'includes a salto.'
                    ),
                ),
                (
                    4,
                    (
                        'Acro in Different Directions '
                        '(Backward + Forward/Sideward)'
                    ),
                    '',
                ),
            ],
        }


        for (
            level_code,
            requirements,
        ) in beam_requirements.items():

            for (
                number,
                title,
                description,
            ) in requirements:

                add_requirement(
                    level_code,
                    'beam',
                    title,
                    PathwayRequirement.TYPE_CR,
                    number,
                    description=description,
                    requirement_number=number,
                    value=0.5,
                )


        # ========================================================
        # BEAM — SEPARATE BONUS
        # ========================================================

        add_requirement(
            'youth_1',
            'beam',
            'Two Flight Elements Bonus',
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus when the acro series '
                'contains two flight elements.'
            ),
            bonus_value=0.1,
            is_required=False,
        )


        # ========================================================
        # FLOOR — CORE REQUIREMENTS
        # ========================================================

        floor_requirements = {

            'aspire': [
                (
                    1,
                    (
                        'Dance Passage of Minimum '
                        '2 Different Leaps or Hops '
                        'with 180° Split'
                    ),
                    (
                        '+0.1 bonus for a '
                        'C-valued leap.'
                    ),
                ),
                (
                    2,
                    (
                        'Stretched Salto Forward '
                        'or Backward in Acro Line'
                    ),
                    (
                        '+0.1 bonus for 180° backward LA. '
                        '+0.3 bonus for 360° backward LA.'
                    ),
                ),
                (
                    3,
                    (
                        'Forward and '
                        'Backward Salto'
                    ),
                    (
                        '+0.3 bonus if performed '
                        'in a combination line.'
                    ),
                ),
                (
                    4,
                    'B Pirouette',
                    '',
                ),
                (
                    5,
                    (
                        'Minimum 3 Acro Lines '
                        'with Minimum 2 Flight Elements '
                        'Including One Salto'
                    ),
                    '',
                ),
            ],

            'youth_1': [
                (
                    1,
                    (
                        'Dance Passage of Minimum '
                        '2 Different Leaps or Hops '
                        'with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    (
                        'Stretched Salto Forward '
                        'or Backward in Acro Line'
                    ),
                    (
                        '+0.1 bonus for 360° '
                        'longitudinal-axis rotation.'
                    ),
                ),
                (
                    3,
                    (
                        'Forward and '
                        'Backward Salto'
                    ),
                    '',
                ),
                (
                    4,
                    'B Pirouette',
                    '',
                ),
            ],

            'youth_2': [
                (
                    1,
                    (
                        'Dance Passage of Minimum '
                        '2 Different Leaps or Hops '
                        'with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    (
                        'Stretched Salto Forward '
                        'or Backward with 360° '
                        'in Acro Line'
                    ),
                    (
                        '+0.1 bonus for 720° '
                        'longitudinal-axis rotation.'
                    ),
                ),
                (
                    3,
                    (
                        'Forward and '
                        'Backward Salto'
                    ),
                    '',
                ),
                (
                    4,
                    'B Pirouette',
                    '',
                ),
            ],

            'youth_3': [
                (
                    1,
                    (
                        'Dance Passage of Minimum '
                        '2 Different Leaps or Hops '
                        'with 180° Split'
                    ),
                    '',
                ),
                (
                    2,
                    (
                        'Stretched Salto with Minimum '
                        '360° Longitudinal Axis Rotation '
                        'in Acro Line'
                    ),
                    (
                        '+0.1 bonus for 720° '
                        'longitudinal-axis rotation.'
                    ),
                ),
                (
                    3,
                    (
                        'Forward and '
                        'Backward Salto'
                    ),
                    '',
                ),
                (
                    4,
                    'B Pirouette',
                    '',
                ),
            ],
        }


        for (
            level_code,
            requirements,
        ) in floor_requirements.items():

            for (
                number,
                title,
                description,
            ) in requirements:

                add_requirement(
                    level_code,
                    'floor',
                    title,
                    PathwayRequirement.TYPE_CR,
                    number,
                    description=description,
                    requirement_number=number,
                    value=0.5,
                )


        # ========================================================
        # FLOOR — SEPARATE BONUS
        # ========================================================

        add_requirement(
            'youth_3',
            'floor',
            'Double Back Salto Bonus',
            PathwayRequirement.TYPE_BONUS,
            20,
            description=(
                'Bonus for a double '
                'backward salto.'
            ),
            bonus_value=0.4,
            is_required=False,
        )


        # ========================================================
        # COMPLETE
        # ========================================================

        requirement_count = (
            PathwayRequirement.objects
            .filter(
                level__code__in=[
                    'aspire',
                    'youth_1',
                    'youth_2',
                    'youth_3',
                ],
                event__code__in=[
                    'vault',
                    'bars',
                    'beam',
                    'floor',
                ],
            )
            .count()
        )


        self.stdout.write(
            self.style.SUCCESS(
                (
                    'High Performance pathway '
                    'rebuilt successfully.'
                )
            )
        )


        self.stdout.write(
            self.style.SUCCESS(
                (
                    f'{requirement_count} official '
                    'requirements are now loaded.'
                )
            )
        )