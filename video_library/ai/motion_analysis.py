from typing import Any


def _safe_float(
    value,
):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _difference(
    current,
    previous,
):
    current = _safe_float(
        current
    )

    previous = _safe_float(
        previous
    )

    if (
        current is None
        or previous is None
    ):
        return None

    return round(
        current - previous,
        3,
    )


def calculate_motion_metrics(
    previous_measurements: dict[str, Any] | None,
    current_measurements: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare two sequential analyzed frames.

    Positive angle change means the measured angle opened.
    Negative angle change means it closed.
    """

    if not previous_measurements:
        return {
            'has_previous_frame': False,
        }

    previous_gymnastics = (
        previous_measurements.get(
            'gymnastics_measurements'
        )
        or {}
    )

    current_gymnastics = (
        current_measurements.get(
            'gymnastics_measurements'
        )
        or {}
    )


    def average_angle(
        measurements,
        key,
    ):
        section = (
            measurements.get(
                key
            )
            or {}
        )

        return section.get(
            'average_angle'
        )


    previous_hip = average_angle(
        previous_gymnastics,
        'hip_position',
    )

    current_hip = average_angle(
        current_gymnastics,
        'hip_position',
    )

    previous_knee = average_angle(
        previous_gymnastics,
        'knee_extension',
    )

    current_knee = average_angle(
        current_gymnastics,
        'knee_extension',
    )

    previous_shoulder = average_angle(
        previous_gymnastics,
        'shoulder_position',
    )

    current_shoulder = average_angle(
        current_gymnastics,
        'shoulder_position',
    )


    previous_torso = (
        previous_gymnastics.get(
            'left_torso_orientation'
        )
    )

    current_torso = (
        current_gymnastics.get(
            'left_torso_orientation'
        )
    )


    hip_change = _difference(
        current_hip,
        previous_hip,
    )

    knee_change = _difference(
        current_knee,
        previous_knee,
    )

    shoulder_change = _difference(
        current_shoulder,
        previous_shoulder,
    )

    torso_change = _difference(
        current_torso,
        previous_torso,
    )


    movement_score = 0.0

    for value in [
        hip_change,
        knee_change,
        shoulder_change,
        torso_change,
    ]:
        if value is None:
            continue

        movement_score += abs(
            value
        )

    movement_score = round(
        movement_score,
        3,
    )


    return {
        'has_previous_frame': True,

        'hip_angle_change': (
            hip_change
        ),

        'knee_angle_change': (
            knee_change
        ),

        'shoulder_angle_change': (
            shoulder_change
        ),

        'torso_orientation_change': (
            torso_change
        ),

        'movement_score': (
            movement_score
        ),
    }