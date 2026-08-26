from typing import Any


def _clamp(
    value,
    minimum=0.0,
    maximum=1.0,
):
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def calculate_frame_score(
    measurements: dict[str, Any],
) -> dict[str, Any]:
    """
    Score how useful an analyzed frame is.

    Score range:
    0.0 - 1.0

    Factors:
    - pose detection
    - landmark visibility
    - phase confidence
    - joint-angle availability
    - movement significance
    - stable peak-position bonus
    """

    if not measurements.get(
        'pose_detected'
    ):
        return {
            'score': 0.0,
            'reasons': [
                'No pose detected.',
            ],
        }


    gymnastics = (
        measurements.get(
            'gymnastics_measurements'
        )
        or {}
    )

    motion = (
        measurements.get(
            'motion_metrics'
        )
        or {}
    )

    phase = (
        measurements.get(
            'skill_phase'
        )
    )

    visibility = (
        gymnastics.get(
            'average_landmark_visibility'
        )
    )

    phase_confidence = (
        measurements.get(
            'skill_phase_confidence'
        )
    )

    pose_angles = (
        measurements.get(
            'pose_angles'
        )
        or {}
    )

    movement_score = (
        motion.get(
            'movement_score'
        )
        or 0.0
    )


    score = 0.0
    reasons = []


    #
    # Pose detected.
    #
    score += 0.20

    reasons.append(
        'Pose detected.'
    )


    #
    # Landmark visibility.
    #
    if visibility is not None:

        visibility = _clamp(
            float(
                visibility
            )
        )

        score += (
            visibility
            * 0.25
        )

        reasons.append(
            (
                'Landmark visibility '
                f'{visibility:.3f}.'
            )
        )


    #
    # Phase confidence.
    #
    if phase_confidence is not None:

        phase_confidence = _clamp(
            float(
                phase_confidence
            )
        )

        score += (
            phase_confidence
            * 0.15
        )

        reasons.append(
            (
                'Phase confidence '
                f'{phase_confidence:.3f}.'
            )
        )


    #
    # Joint-angle coverage.
    #
    angle_count = len(
        pose_angles
    )

    if angle_count >= 6:
        score += 0.10

    elif angle_count >= 3:
        score += 0.05

    reasons.append(
        (
            f'{angle_count} usable '
            'joint-angle measurements.'
        )
    )


    #
    # Motion-aware scoring.
    #
    # Large movement is useful for transitions.
    #
    if movement_score >= 20:

        score += 0.18

        reasons.append(
            'High movement-change frame.'
        )

    elif movement_score >= 10:

        score += 0.12

        reasons.append(
            'Moderate movement-change frame.'
        )

    elif movement_score >= 4:

        score += 0.06

        reasons.append(
            'Some movement change detected.'
        )


    #
    # Stable peak bonus.
    #
    if (
        phase == 'peak'
        and movement_score < 8
    ):
        score += 0.18

        reasons.append(
            (
                'Stable peak-position frame.'
            )
        )


    #
    # Setup and finish stability can also be useful.
    #
    if (
        phase in [
            'setup',
            'finish',
        ]
        and movement_score < 6
    ):
        score += 0.05

        reasons.append(
            (
                'Stable boundary-phase frame.'
            )
        )


    score = round(
        _clamp(
            score
        ),
        3,
    )


    return {
        'score': score,
        'reasons': reasons,
    }