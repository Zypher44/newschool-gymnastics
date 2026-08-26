from typing import Any


MEASUREMENT_LABELS = {
    'knee_angle': 'Knee Angle',
    'hip_angle': 'Hip Angle',
    'shoulder_angle': 'Shoulder Angle',
    'elbow_angle': 'Elbow Angle',
}


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


def _build_change(
    *,
    phase_name,
    phase_label,
    measurement_name,
    first_value,
    second_value,
):
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
        return None

    delta = round(
        second_value
        - first_value,
        1,
    )

    return {
        'phase': phase_name,

        'phase_label': (
            phase_label
        ),

        'measurement': (
            measurement_name
        ),

        'measurement_label': (
            MEASUREMENT_LABELS.get(
                measurement_name,
                measurement_name
                .replace(
                    '_',
                    ' ',
                )
                .title(),
            )
        ),

        'first': round(
            first_value,
            1,
        ),

        'second': round(
            second_value,
            1,
        ),

        'delta': delta,

        'absolute_delta': round(
            abs(delta),
            1,
        ),

        'direction': (
            'increased'
            if delta > 0
            else (
                'decreased'
                if delta < 0
                else 'unchanged'
            )
        ),
    }


def build_comparison_summary(
    phase_comparisons: list[dict[str, Any]],
):
    """
    Build an objective summary of the largest differences
    between two analyzed attempts.

    Important:
    This function reports measurement change only.

    It does NOT assume that a larger or smaller angle is
    automatically better.
    """

    changes = []

    timing_changes = []


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


        for measurement_name in [
            'knee_angle',
            'hip_angle',
            'shoulder_angle',
            'elbow_angle',
        ]:

            change = _build_change(
                phase_name=(
                    phase.get(
                        'name'
                    )
                ),

                phase_label=(
                    phase.get(
                        'label'
                    )
                ),

                measurement_name=(
                    measurement_name
                ),

                first_value=(
                    first.get(
                        measurement_name
                    )
                ),

                second_value=(
                    second.get(
                        measurement_name
                    )
                ),
            )


            if change:
                changes.append(
                    change
                )


        first_timestamp = (
            _safe_float(
                first.get(
                    'timestamp'
                )
            )
        )

        second_timestamp = (
            _safe_float(
                second.get(
                    'timestamp'
                )
            )
        )


        if (
            first_timestamp is not None
            and second_timestamp is not None
        ):

            timing_delta = round(
                second_timestamp
                - first_timestamp,
                2,
            )

            timing_changes.append({
                'phase': (
                    phase.get(
                        'name'
                    )
                ),

                'phase_label': (
                    phase.get(
                        'label'
                    )
                ),

                'first': round(
                    first_timestamp,
                    2,
                ),

                'second': round(
                    second_timestamp,
                    2,
                ),

                'delta': (
                    timing_delta
                ),

                'absolute_delta': round(
                    abs(
                        timing_delta
                    ),
                    2,
                ),

                'direction': (
                    'later'
                    if timing_delta > 0
                    else (
                        'earlier'
                        if timing_delta < 0
                        else 'same'
                    )
                ),
            })


    #
    # Largest measurement differences first.
    #
    changes = sorted(
        changes,
        key=lambda item: (
            item[
                'absolute_delta'
            ]
        ),
        reverse=True,
    )


    timing_changes = sorted(
        timing_changes,
        key=lambda item: (
            item[
                'absolute_delta'
            ]
        ),
        reverse=True,
    )


    #
    # Ignore tiny angle differences in the
    # headline summary.
    #
    meaningful_changes = [
        change
        for change in changes
        if (
            change[
                'absolute_delta'
            ] >= 3.0
        )
    ]


    #
    # Keep the UI concise.
    #
    top_changes = (
        meaningful_changes[:6]
    )


    largest_change = (
        top_changes[0]
        if top_changes
        else None
    )


    largest_timing_change = (
        timing_changes[0]
        if timing_changes
        else None
    )


    return {
        'largest_change': (
            largest_change
        ),

        'top_changes': (
            top_changes
        ),

        'all_changes': (
            changes
        ),

        'timing_changes': (
            timing_changes
        ),

        'largest_timing_change': (
            largest_timing_change
        ),

        'meaningful_change_count': (
            len(
                meaningful_changes
            )
        ),
    }