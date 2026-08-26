import math
from typing import Any


def calculate_angle(
    point_a: dict[str, float],
    point_b: dict[str, float],
    point_c: dict[str, float],
) -> float | None:
    """
    Calculate the angle ABC in degrees.

    point_b is the joint/vertex.
    """

    try:
        ax = float(point_a['x'])
        ay = float(point_a['y'])

        bx = float(point_b['x'])
        by = float(point_b['y'])

        cx = float(point_c['x'])
        cy = float(point_c['y'])

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    vector_ba = (
        ax - bx,
        ay - by,
    )

    vector_bc = (
        cx - bx,
        cy - by,
    )

    magnitude_ba = math.sqrt(
        vector_ba[0] ** 2
        + vector_ba[1] ** 2
    )

    magnitude_bc = math.sqrt(
        vector_bc[0] ** 2
        + vector_bc[1] ** 2
    )

    if (
        magnitude_ba == 0
        or magnitude_bc == 0
    ):
        return None

    dot_product = (
        vector_ba[0] * vector_bc[0]
        + vector_ba[1] * vector_bc[1]
    )

    cosine_angle = (
        dot_product
        / (
            magnitude_ba
            * magnitude_bc
        )
    )

    cosine_angle = max(
        -1.0,
        min(
            1.0,
            cosine_angle,
        ),
    )

    angle_radians = math.acos(
        cosine_angle
    )

    return round(
        math.degrees(
            angle_radians
        ),
        1,
    )


def calculate_pose_angles(
    landmarks: dict[str, Any],
) -> dict[str, float]:
    """
    Calculate important gymnastics joint angles
    from MediaPipe pose landmarks.
    """

    angles = {}


    def add_angle(
        name,
        point_a_name,
        point_b_name,
        point_c_name,
    ):
        point_a = landmarks.get(
            point_a_name
        )

        point_b = landmarks.get(
            point_b_name
        )

        point_c = landmarks.get(
            point_c_name
        )

        if not all([
            point_a,
            point_b,
            point_c,
        ]):
            return

        angle = calculate_angle(
            point_a,
            point_b,
            point_c,
        )

        if angle is not None:
            angles[name] = angle


    # Elbows
    add_angle(
        'left_elbow_angle',
        'left_shoulder',
        'left_elbow',
        'left_wrist',
    )

    add_angle(
        'right_elbow_angle',
        'right_shoulder',
        'right_elbow',
        'right_wrist',
    )


    # Shoulders
    add_angle(
        'left_shoulder_angle',
        'left_elbow',
        'left_shoulder',
        'left_hip',
    )

    add_angle(
        'right_shoulder_angle',
        'right_elbow',
        'right_shoulder',
        'right_hip',
    )


    # Hips
    add_angle(
        'left_hip_angle',
        'left_shoulder',
        'left_hip',
        'left_knee',
    )

    add_angle(
        'right_hip_angle',
        'right_shoulder',
        'right_hip',
        'right_knee',
    )


    # Knees
    add_angle(
        'left_knee_angle',
        'left_hip',
        'left_knee',
        'left_ankle',
    )

    add_angle(
        'right_knee_angle',
        'right_hip',
        'right_knee',
        'right_ankle',
    )

    return angles


def generate_mock_measurements() -> dict[str, Any]:
    """
    Existing mock results used by the mock analysis engine.
    """

    return {
        'demonstration_only': True,
        'shoulder_angle_degrees': 171.4,
        'hip_angle_degrees': 166.8,
        'knee_angle_degrees': 174.2,
        'estimated_skill_duration_seconds': 2.85,
    }