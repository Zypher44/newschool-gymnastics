from .skill_interpretation import (
    interpret_measurement_change,
)

from .technique_profile_service import (
    get_profile_settings,
)


MEASUREMENTS = [
    'knee_angle',
    'hip_angle',
    'shoulder_angle',
    'elbow_angle',
]

def build_coaching_interpretation(
    *,
    skill_name,
    phase_comparisons,
):

    profile_settings = (
        get_profile_settings(
            skill_name
        )
    )


    interpretations = []


    for phase in phase_comparisons:

        first = (
            phase.get(
                'first'
            )
            or {}
        )

        second = (
            phase.get(
                'second'
            )
            or {}
        )


        if (
            not first
            or not second
        ):
            continue


        for measurement in MEASUREMENTS:

            result = (
                interpret_measurement_change(

                    skill_name=(
                        skill_name
                    ),

                    phase=(
                        phase[
                            'name'
                        ]
                    ),

                    phase_label=(
                        phase[
                            'label'
                        ]
                    ),

                    measurement=(
                        measurement
                    ),

                    first_value=(
                        first.get(
                            measurement
                        )
                    ),

                    second_value=(
                        second.get(
                            measurement
                        )
                    ),
                )
            )


            #
            # Skip measurements that are missing
            # OR disabled by the coaching profile.
            #
            if not result.get(
                'evidence'
            ):
                continue


            interpretations.append({

                'phase': (
                    phase[
                        'name'
                    ]
                ),

                'phase_label': (
                    phase[
                        'label'
                    ]
                ),

                'measurement': (
                    measurement
                ),

                'status': (
                    result[
                        'status'
                    ]
                ),

                'message': (
                    result[
                        'message'
                    ]
                ),

                'evidence': (
                    result[
                        'evidence'
                    ]
                ),

                'rule_available': (
                    result[
                        'rule_available'
                    ]
                ),

                'profile_enabled': (
                    result.get(
                        'profile_enabled',
                        True,
                    )
                ),

                'rule': (
                    result.get(
                        'rule'
                    )
                ),
            })


    improved = [
        item
        for item in interpretations
        if item[
            'status'
        ] == 'improved'
    ]


    review = [
        item
        for item in interpretations
        if item[
            'status'
        ] == 'review'
    ]


    similar = [
        item
        for item in interpretations
        if item[
            'status'
        ] == 'similar'
    ]


    neutral = [
        item
        for item in interpretations
        if item[
            'status'
        ] == 'neutral'
    ]


    improved = sorted(
        improved,
        key=lambda item: abs(
            item[
                'evidence'
            ].get(
                'change_toward_target',
                0,
            )
        ),
        reverse=True,
    )


    review = sorted(
        review,
        key=lambda item: abs(
            item[
                'evidence'
            ].get(
                'change_toward_target',
                0,
            )
        ),
        reverse=True,
    )


    return {

        'skill_name': (
            skill_name
        ),

        'interpretations': (
            interpretations
        ),

        'improved': (
            improved[:5]
        ),

        'review': (
            review[:5]
        ),

        'similar': (
            similar[:5]
        ),

        'neutral': (
            neutral[:5]
        ),

        'rule_based_count': len([
            item
            for item in interpretations
            if item[
                'rule_available'
            ]
        ]),

        'has_skill_rules': any(
            item[
                'rule_available'
            ]
            for item in interpretations
        ),

        #
        # Technique Profile information
        #
        'profile': (
            profile_settings
        ),

        'using_custom_profile': (
            profile_settings
            is not None
        ),
    }