from typing import Any
from .technique_profile_service import (
    get_profile_settings,
)

STATUS_IMPROVED = 'improved'
STATUS_SIMILAR = 'similar'
STATUS_REVIEW = 'review'
STATUS_NEUTRAL = 'neutral'


SKILL_RULES = {

    'handstand': {

        'peak': {

            'knee_angle': {
                'label': 'Knee Extension',
                'target': 180.0,
                'tolerance': 3.0,
            },

            'hip_angle': {
                'label': 'Hip Extension',
                'target': 180.0,
                'tolerance': 4.0,
            },

            'shoulder_angle': {
                'label': 'Shoulder Opening',
                'target': 180.0,
                'tolerance': 5.0,
            },

            'elbow_angle': {
                'label': 'Elbow Extension',
                'target': 180.0,
                'tolerance': 3.0,
            },
        },
    },


    'cast handstand': {

        'main_action': {

            'knee_angle': {
                'label': 'Knee Extension',
                'target': 180.0,
                'tolerance': 4.0,
            },

            'hip_angle': {
                'label': 'Hip Extension',
                'target': 180.0,
                'tolerance': 5.0,
            },

            'shoulder_angle': {
                'label': 'Shoulder Opening',
                'target': 180.0,
                'tolerance': 6.0,
            },
        },

        'peak': {

            'knee_angle': {
                'label': 'Knee Extension',
                'target': 180.0,
                'tolerance': 3.0,
            },

            'hip_angle': {
                'label': 'Hip Extension',
                'target': 180.0,
                'tolerance': 4.0,
            },

            'shoulder_angle': {
                'label': 'Shoulder Opening',
                'target': 180.0,
                'tolerance': 5.0,
            },

            'elbow_angle': {
                'label': 'Elbow Extension',
                'target': 180.0,
                'tolerance': 3.0,
            },
        },
    },


    'back handspring': {

        'entry': {

            'knee_angle': {
                'label': 'Entry Knee Position',
                'target': 135.0,
                'tolerance': 12.0,
            },

            'hip_angle': {
                'label': 'Entry Hip Position',
                'target': 150.0,
                'tolerance': 12.0,
            },
        },

        'main_action': {

            'shoulder_angle': {
                'label': 'Shoulder Opening',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'elbow_angle': {
                'label': 'Elbow Extension',
                'target': 180.0,
                'tolerance': 5.0,
            },
        },

        'peak': {

            'hip_angle': {
                'label': 'Body Line',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'knee_angle': {
                'label': 'Leg Extension',
                'target': 180.0,
                'tolerance': 6.0,
            },
        },
    },


    'roundoff': {

        'entry': {

            'knee_angle': {
                'label': 'Entry Leg Extension',
                'target': 175.0,
                'tolerance': 7.0,
            },
        },

        'main_action': {

            'shoulder_angle': {
                'label': 'Shoulder Position',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'elbow_angle': {
                'label': 'Arm Support',
                'target': 180.0,
                'tolerance': 5.0,
            },
        },

        'peak': {

            'hip_angle': {
                'label': 'Body Alignment',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'knee_angle': {
                'label': 'Leg Extension',
                'target': 180.0,
                'tolerance': 6.0,
            },
        },
    },


    'front handspring': {

        'entry': {

            'knee_angle': {
                'label': 'Entry Leg Extension',
                'target': 175.0,
                'tolerance': 7.0,
            },
        },

        'main_action': {

            'shoulder_angle': {
                'label': 'Shoulder Opening',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'elbow_angle': {
                'label': 'Arm Extension',
                'target': 180.0,
                'tolerance': 5.0,
            },
        },

        'peak': {

            'hip_angle': {
                'label': 'Body Line',
                'target': 180.0,
                'tolerance': 8.0,
            },

            'knee_angle': {
                'label': 'Leg Extension',
                'target': 180.0,
                'tolerance': 6.0,
            },
        },
    },


    'back tuck': {

        'entry': {

            'knee_angle': {
                'label': 'Takeoff Knee Position',
                'target': 150.0,
                'tolerance': 15.0,
            },

            'hip_angle': {
                'label': 'Takeoff Hip Position',
                'target': 160.0,
                'tolerance': 15.0,
            },
        },

        'main_action': {

            'knee_angle': {
                'label': 'Tuck Knee Position',
                'target': 75.0,
                'tolerance': 15.0,
            },

            'hip_angle': {
                'label': 'Tuck Hip Position',
                'target': 70.0,
                'tolerance': 15.0,
            },
        },

        'exit': {

            'knee_angle': {
                'label': 'Opening Knee Position',
                'target': 170.0,
                'tolerance': 10.0,
            },

            'hip_angle': {
                'label': 'Opening Hip Position',
                'target': 170.0,
                'tolerance': 10.0,
            },
        },

        'finish': {

            'knee_angle': {
                'label': 'Landing Knee Position',
                'target': 155.0,
                'tolerance': 15.0,
            },
        },
    },
}


SKILL_ALIASES = {
    'cast to handstand': 'cast handstand',
    'cast-handstand': 'cast handstand',

    'bhs': 'back handspring',
    'backhandspring': 'back handspring',

    'fhs': 'front handspring',
    'fronthandspring': 'front handspring',

    'back salto tuck': 'back tuck',
    'backward tuck': 'back tuck',

    'round off': 'roundoff',
}


def normalize_skill_name(
    skill_name,
):
    normalized = (
        skill_name
        or ''
    ).strip().lower()

    normalized = ' '.join(
        normalized.split()
    )

    return SKILL_ALIASES.get(
        normalized,
        normalized,
    )


def _safe_float(
    value,
):
    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def get_skill_rule(
    *,
    skill_name,
    phase,
    measurement,
):
    normalized_skill = (
        normalize_skill_name(
            skill_name
        )
    )

    skill_rules = (
        SKILL_RULES.get(
            normalized_skill
        )
        or {}
    )

    phase_rules = (
        skill_rules.get(
            phase
        )
        or {}
    )

    return phase_rules.get(
        measurement
    )


def interpret_measurement_change(
    *,
    skill_name,
    phase,
    phase_label,
    measurement,
    first_value,
    second_value,
) -> dict[str, Any]:

    first_value = _safe_float(
        first_value
    )

    second_value = _safe_float(
        second_value
    )


    if (
        first_value is None
        or second_value is None
    ):
        return {
            'status': STATUS_NEUTRAL,
            'message': (
                'Not enough measurement data '
                'was available for interpretation.'
            ),
            'evidence': None,
            'rule_available': False,
            'profile_enabled': False,
        }


    #
    # ---------------------------------------------------------
    # BUILT-IN SKILL RULE
    # ---------------------------------------------------------
    #

    rule = get_skill_rule(
        skill_name=skill_name,
        phase=phase,
        measurement=measurement,
    )


    #
    # ---------------------------------------------------------
    # CUSTOM COACH TECHNIQUE PROFILE
    # ---------------------------------------------------------
    #

    profile_settings = (
        get_profile_settings(
            skill_name
        )
    )


    #
    # If a custom profile exists, only interpret
    # measurements the coach selected as priorities.
    #
    if profile_settings:

        selected_measurements = (
            profile_settings.get(
                'measurements',
                [],
            )
        )


        if (
            measurement
            not in selected_measurements
        ):
            return {
                'status': STATUS_NEUTRAL,

                'message': (
                    'This measurement is not part '
                    'of the current coaching profile.'
                ),

                'evidence': None,

                'rule_available': (
                    bool(rule)
                ),

                'profile_enabled': False,

                'profile': (
                    profile_settings
                ),
            }


    delta = round(
        second_value
        - first_value,
        1,
    )


    #
    # ---------------------------------------------------------
    # NO BUILT-IN TECHNICAL RULE
    # ---------------------------------------------------------
    #

    if not rule:

        return {
            'status': STATUS_NEUTRAL,

            'message': (
                f'{phase_label}: '
                f'{measurement.replace("_", " ").title()} '
                f'changed from {first_value:.1f}° '
                f'to {second_value:.1f}°.'
            ),

            'evidence': {
                'first': round(
                    first_value,
                    1,
                ),

                'second': round(
                    second_value,
                    1,
                ),

                'delta': delta,
            },

            'rule_available': False,

            'profile_enabled': True,

            'profile': (
                profile_settings
            ),
        }


    #
    # ---------------------------------------------------------
    # TARGET + TOLERANCE
    # ---------------------------------------------------------
    #

    target = float(
        rule[
            'target'
        ]
    )


    base_tolerance = float(
        rule.get(
            'tolerance',
            3.0,
        )
    )


    #
    # Custom profile changes how sensitive
    # the comparison is.
    #
    tolerance_multiplier = 1.0


    if profile_settings:

        tolerance_multiplier = float(
            profile_settings.get(
                'tolerance_multiplier',
                1.0,
            )
        )


    tolerance = round(
        base_tolerance
        * tolerance_multiplier,
        2,
    )


    first_distance = abs(
        target
        - first_value
    )

    second_distance = abs(
        target
        - second_value
    )


    improvement = round(
        first_distance
        - second_distance,
        1,
    )


    label = rule.get(
        'label',
        measurement
        .replace(
            '_',
            ' ',
        )
        .title(),
    )


    #
    # ---------------------------------------------------------
    # INTERPRET RESULT
    # ---------------------------------------------------------
    #

    if abs(
        improvement
    ) <= tolerance:

        status = (
            STATUS_SIMILAR
        )

        message = (
            f'{phase_label} {label} stayed '
            'within the current coaching range.'
        )


    elif improvement > 0:

        status = (
            STATUS_IMPROVED
        )

        message = (
            f'{phase_label} {label} moved '
            'closer to the current technique reference.'
        )


    else:

        status = (
            STATUS_REVIEW
        )

        message = (
            f'{phase_label} {label} moved '
            'farther from the current technique reference.'
        )


    return {
        'status': status,

        'message': message,

        'evidence': {

            'first': round(
                first_value,
                1,
            ),

            'second': round(
                second_value,
                1,
            ),

            'delta': delta,

            'target': round(
                target,
                1,
            ),

            'first_distance_from_target': round(
                first_distance,
                1,
            ),

            'second_distance_from_target': round(
                second_distance,
                1,
            ),

            'change_toward_target': (
                improvement
            ),

            'tolerance_used': (
                tolerance
            ),
        },

        'rule_available': True,

        'profile_enabled': True,

        'profile': (
            profile_settings
        ),

        'rule': {

            'skill': (
                normalize_skill_name(
                    skill_name
                )
            ),

            'phase': phase,

            'measurement': (
                measurement
            ),

            'target': target,

            'base_tolerance': (
                base_tolerance
            ),

            'effective_tolerance': (
                tolerance
            ),
        },
    }