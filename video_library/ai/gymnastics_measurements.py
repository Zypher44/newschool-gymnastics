import math
from typing import Any


def _get_point(
    landmarks: dict[str, Any],
    name: str,
):
    point = landmarks.get(name)

    if not point:
        return None

    try:
        return {
            'x': float(point['x']),
            'y': float(point['y']),
            'z': float(point.get('z', 0.0)),
            'visibility': (
                float(point['visibility'])
                if point.get('visibility') is not None
                else None
            ),
        }

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


def _distance_2d(
    point_a,
    point_b,
):
    return math.sqrt(
        (
            point_b['x']
            - point_a['x']
        ) ** 2
        +
        (
            point_b['y']
            - point_a['y']
        ) ** 2
    )


def _orientation_degrees(
    point_a,
    point_b,
):
    """
    Return orientation of line AB relative to image horizontal.

    0 degrees = horizontal
    90 degrees = vertical
    """

    delta_x = (
        point_b['x']
        - point_a['x']
    )

    delta_y = (
        point_b['y']
        - point_a['y']
    )

    angle = math.degrees(
        math.atan2(
            abs(delta_y),
            abs(delta_x),
        )
    )

    return round(
        angle,
        1,
    )


def _average(
    values,
):
    valid_values = [
        value
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return round(
        sum(valid_values)
        / len(valid_values),
        1,
    )


def _difference(
    left_value,
    right_value,
):
    if (
        left_value is None
        or right_value is None
    ):
        return None

    return round(
        abs(
            left_value
            - right_value
        ),
        1,
    )


def _classify_extension(
    angle,
):
    """
    Neutral descriptive classification.

    This is not a coaching judgment.
    """

    if angle is None:
        return None

    if angle >= 170:
        return 'nearly_straight'

    if angle >= 150:
        return 'slightly_bent'

    if angle >= 120:
        return 'moderately_bent'

    return 'deeply_bent'


def calculate_gymnastics_measurements(
    landmarks: dict[str, Any],
    pose_angles: dict[str, float],
) -> dict[str, Any]:
    """
    Convert pose landmarks and joint angles into structured,
    gymnastics-relevant objective measurements.
    """

    left_shoulder = _get_point(
        landmarks,
        'left_shoulder',
    )

    right_shoulder = _get_point(
        landmarks,
        'right_shoulder',
    )

    left_hip = _get_point(
        landmarks,
        'left_hip',
    )

    right_hip = _get_point(
        landmarks,
        'right_hip',
    )

    left_ankle = _get_point(
        landmarks,
        'left_ankle',
    )

    right_ankle = _get_point(
        landmarks,
        'right_ankle',
    )


    left_elbow_angle = (
        pose_angles.get(
            'left_elbow_angle'
        )
    )

    right_elbow_angle = (
        pose_angles.get(
            'right_elbow_angle'
        )
    )

    left_shoulder_angle = (
        pose_angles.get(
            'left_shoulder_angle'
        )
    )

    right_shoulder_angle = (
        pose_angles.get(
            'right_shoulder_angle'
        )
    )

    left_hip_angle = (
        pose_angles.get(
            'left_hip_angle'
        )
    )

    right_hip_angle = (
        pose_angles.get(
            'right_hip_angle'
        )
    )

    left_knee_angle = (
        pose_angles.get(
            'left_knee_angle'
        )
    )

    right_knee_angle = (
        pose_angles.get(
            'right_knee_angle'
        )
    )


    measurements = {
        'elbow_extension': {
            'left_angle': (
                left_elbow_angle
            ),
            'right_angle': (
                right_elbow_angle
            ),
            'average_angle': _average([
                left_elbow_angle,
                right_elbow_angle,
            ]),
            'left_position': (
                _classify_extension(
                    left_elbow_angle
                )
            ),
            'right_position': (
                _classify_extension(
                    right_elbow_angle
                )
            ),
            'symmetry_difference': (
                _difference(
                    left_elbow_angle,
                    right_elbow_angle,
                )
            ),
        },

        'knee_extension': {
            'left_angle': (
                left_knee_angle
            ),
            'right_angle': (
                right_knee_angle
            ),
            'average_angle': _average([
                left_knee_angle,
                right_knee_angle,
            ]),
            'left_position': (
                _classify_extension(
                    left_knee_angle
                )
            ),
            'right_position': (
                _classify_extension(
                    right_knee_angle
                )
            ),
            'symmetry_difference': (
                _difference(
                    left_knee_angle,
                    right_knee_angle,
                )
            ),
        },

        'hip_position': {
            'left_angle': (
                left_hip_angle
            ),
            'right_angle': (
                right_hip_angle
            ),
            'average_angle': _average([
                left_hip_angle,
                right_hip_angle,
            ]),
            'symmetry_difference': (
                _difference(
                    left_hip_angle,
                    right_hip_angle,
                )
            ),
        },

        'shoulder_position': {
            'left_angle': (
                left_shoulder_angle
            ),
            'right_angle': (
                right_shoulder_angle
            ),
            'average_angle': _average([
                left_shoulder_angle,
                right_shoulder_angle,
            ]),
            'symmetry_difference': (
                _difference(
                    left_shoulder_angle,
                    right_shoulder_angle,
                )
            ),
        },
    }


    if (
        left_shoulder
        and right_shoulder
    ):
        measurements[
            'shoulder_line'
        ] = {
            'width_normalized': (
                round(
                    _distance_2d(
                        left_shoulder,
                        right_shoulder,
                    ),
                    4,
                )
            ),
            'orientation_degrees': (
                _orientation_degrees(
                    left_shoulder,
                    right_shoulder,
                )
            ),
        }


    if (
        left_hip
        and right_hip
    ):
        measurements[
            'hip_line'
        ] = {
            'width_normalized': (
                round(
                    _distance_2d(
                        left_hip,
                        right_hip,
                    ),
                    4,
                )
            ),
            'orientation_degrees': (
                _orientation_degrees(
                    left_hip,
                    right_hip,
                )
            ),
        }


    if (
        left_shoulder
        and left_hip
    ):
        measurements[
            'left_torso_orientation'
        ] = (
            _orientation_degrees(
                left_shoulder,
                left_hip,
            )
        )


    if (
        right_shoulder
        and right_hip
    ):
        measurements[
            'right_torso_orientation'
        ] = (
            _orientation_degrees(
                right_shoulder,
                right_hip,
            )
        )


    if (
        left_hip
        and left_ankle
    ):
        measurements[
            'left_leg_orientation'
        ] = (
            _orientation_degrees(
                left_hip,
                left_ankle,
            )
        )


    if (
        right_hip
        and right_ankle
    ):
        measurements[
            'right_leg_orientation'
        ] = (
            _orientation_degrees(
                right_hip,
                right_ankle,
            )
        )


    visibility_values = []

    for landmark in landmarks.values():
        visibility = (
            landmark.get(
                'visibility'
            )
        )

        if visibility is not None:
            try:
                visibility_values.append(
                    float(
                        visibility
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                pass


    if visibility_values:
        measurements[
            'average_landmark_visibility'
        ] = round(
            sum(
                visibility_values
            )
            / len(
                visibility_values
            ),
            3,
        )


    return measurements