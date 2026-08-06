from typing import Any


def generate_mock_measurements() -> dict[str, Any]:
    """
    Return demonstration measurements.

    These values are not extracted from the uploaded video.
    They only allow the complete analysis workflow to be tested.
    """

    return {
        'demonstration_only': True,
        'shoulder_angle_degrees': 171.4,
        'hip_angle_degrees': 166.8,
        'knee_angle_degrees': 174.2,
        'estimated_skill_duration_seconds': 2.85,
    }