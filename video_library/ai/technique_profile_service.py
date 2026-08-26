from video_library.models import (
    TechniqueProfile,
)


STRICTNESS_TOLERANCE_MULTIPLIERS = {

    TechniqueProfile.STRICTNESS_DEVELOPMENTAL: (
        1.6
    ),

    TechniqueProfile.STRICTNESS_STANDARD: (
        1.0
    ),

    TechniqueProfile.STRICTNESS_HIGH_PERFORMANCE: (
        0.65
    ),
}


DEFAULT_EMPHASIS_MAP = {

    'straight_legs': [
        'knee_angle',
    ],

    'body_line': [
        'hip_angle',
    ],

    'shoulder_position': [
        'shoulder_angle',
    ],

    'straight_arms': [
        'elbow_angle',
    ],

    'landing_control': [
        'knee_angle',
        'hip_angle',
    ],

    'takeoff_position': [
        'knee_angle',
        'hip_angle',
    ],

    'tuck_position': [
        'knee_angle',
        'hip_angle',
    ],
}


def normalize_skill_name(
    skill_name,
):
    return ' '.join(
        (
            skill_name
            or ''
        )
        .strip()
        .lower()
        .split()
    )


def get_technique_profile(
    skill_name,
):
    normalized = (
        normalize_skill_name(
            skill_name
        )
    )

    if not normalized:
        return None

    profiles = (
        TechniqueProfile.objects
        .filter(
            is_active=True,
        )
    )

    for profile in profiles:

        if (
            normalize_skill_name(
                profile.skill_name
            )
            == normalized
        ):
            return profile

    return None


def get_profile_settings(
    skill_name,
):
    """
    Return a simple dictionary describing what
    this program wants emphasized for the skill.
    """

    profile = (
        get_technique_profile(
            skill_name
        )
    )

    if not profile:
        return None


    emphasis_fields = [
        'straight_legs',
        'body_line',
        'shoulder_position',
        'straight_arms',
        'landing_control',
        'takeoff_position',
        'tuck_position',
    ]


    active_emphases = [
        field
        for field in emphasis_fields
        if getattr(
            profile,
            field,
            False,
        )
    ]


    measurements = set()

    for emphasis in active_emphases:

        measurements.update(
            DEFAULT_EMPHASIS_MAP.get(
                emphasis,
                []
            )
        )


    return {

        'profile_id': (
            profile.id
        ),

        'skill_name': (
            profile.skill_name
        ),

        'strictness': (
            profile.strictness
        ),

        'strictness_label': (
            profile
            .get_strictness_display()
        ),

        'tolerance_multiplier': (
            STRICTNESS_TOLERANCE_MULTIPLIERS.get(
                profile.strictness,
                1.0,
            )
        ),

        'active_emphases': (
            active_emphases
        ),

        'active_emphasis_labels': (
            profile.active_emphases
        ),

        'measurements': list(
            measurements
        ),
    }