from typing import Any

from video_library.models import (
    VideoAnalysis,
)


PHASE_ORDER = [
    'setup',
    'entry',
    'main_action',
    'peak',
    'exit',
    'finish',
]


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
    first,
    second,
):
    first = _safe_float(
        first
    )

    second = _safe_float(
        second
    )

    if (
        first is None
        or second is None
    ):
        return None

    return round(
        second - first,
        1,
    )


def _get_average_angle(
    measurements: dict[str, Any],
    section_name: str,
):
    gymnastics = (
        measurements.get(
            'gymnastics_measurements'
        )
        or {}
    )

    section = (
        gymnastics.get(
            section_name
        )
        or {}
    )

    return section.get(
        'average_angle'
    )


def _best_frame_for_phase(
    analysis: VideoAnalysis,
    phase: str,
):
    """
    Choose the strongest available key frame for a phase.

    Falls back to any frame in that phase if no key frame
    exists.
    """

    phase_moments = []

    for moment in (
        analysis.moments
        .exclude(
            frame_image='',
        )
        .order_by(
            'timestamp_seconds',
        )
    ):
        measurements = (
            moment.measurements
            or {}
        )

        if (
            measurements.get(
                'skill_phase'
            )
            != phase
        ):
            continue

        phase_moments.append(
            moment
        )

    if not phase_moments:
        return None


    key_frames = [
        moment
        for moment in phase_moments
        if (
            moment.measurements
            or {}
        ).get(
            'is_key_frame'
        )
    ]


    candidates = (
        key_frames
        or phase_moments
    )


    return max(
        candidates,
        key=lambda moment: (
            float(
                (
                    moment.measurements
                    or {}
                ).get(
                    'frame_quality_score'
                )
                or 0.0
            )
        ),
    )


def _build_phase_comparison(
    phase,
    first_moment,
    second_moment,
):
    first_measurements = (
        first_moment.measurements
        if first_moment
        else {}
    ) or {}

    second_measurements = (
        second_moment.measurements
        if second_moment
        else {}
    ) or {}


    first_knee = (
        _get_average_angle(
            first_measurements,
            'knee_extension',
        )
    )

    second_knee = (
        _get_average_angle(
            second_measurements,
            'knee_extension',
        )
    )


    first_hip = (
        _get_average_angle(
            first_measurements,
            'hip_position',
        )
    )

    second_hip = (
        _get_average_angle(
            second_measurements,
            'hip_position',
        )
    )


    first_shoulder = (
        _get_average_angle(
            first_measurements,
            'shoulder_position',
        )
    )

    second_shoulder = (
        _get_average_angle(
            second_measurements,
            'shoulder_position',
        )
    )


    first_elbow = (
        _get_average_angle(
            first_measurements,
            'elbow_extension',
        )
    )

    second_elbow = (
        _get_average_angle(
            second_measurements,
            'elbow_extension',
        )
    )


    return {
        'phase': phase,

        'first_moment': (
            first_moment
        ),

        'second_moment': (
            second_moment
        ),

        'measurements': {
            'knee': {
                'first': first_knee,
                'second': second_knee,
                'delta': _difference(
                    first_knee,
                    second_knee,
                ),
            },

            'hip': {
                'first': first_hip,
                'second': second_hip,
                'delta': _difference(
                    first_hip,
                    second_hip,
                ),
            },

            'shoulder': {
                'first': first_shoulder,
                'second': second_shoulder,
                'delta': _difference(
                    first_shoulder,
                    second_shoulder,
                ),
            },

            'elbow': {
                'first': first_elbow,
                'second': second_elbow,
                'delta': _difference(
                    first_elbow,
                    second_elbow,
                ),
            },
        },
    }


def compare_analyses(
    first_analysis: VideoAnalysis,
    second_analysis: VideoAnalysis,
):
    """
    Compare two analyses phase by phase.
    """

    phase_comparisons = []


    for phase in PHASE_ORDER:

        first_moment = (
            _best_frame_for_phase(
                first_analysis,
                phase,
            )
        )

        second_moment = (
            _best_frame_for_phase(
                second_analysis,
                phase,
            )
        )


        if (
            not first_moment
            and not second_moment
        ):
            continue


        phase_comparisons.append(
            _build_phase_comparison(
                phase=phase,
                first_moment=(
                    first_moment
                ),
                second_moment=(
                    second_moment
                ),
            )
        )


    return {
        'first_analysis': (
            first_analysis
        ),

        'second_analysis': (
            second_analysis
        ),

        'phase_comparisons': (
            phase_comparisons
        ),
    }