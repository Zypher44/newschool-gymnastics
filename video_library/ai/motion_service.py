from video_library.models import (
    VideoAnalysis,
)

from .motion_analysis import (
    calculate_motion_metrics,
)


def calculate_analysis_motion(
    analysis: VideoAnalysis,
):
    """
    Calculate frame-to-frame movement information
    across all extracted analysis frames.
    """

    moments = list(
        analysis.moments
        .exclude(
            frame_image='',
        )
        .order_by(
            'timestamp_seconds',
        )
    )

    previous_measurements = None

    processed = 0


    for moment in moments:

        measurements = dict(
            moment.measurements
            or {}
        )

        motion = (
            calculate_motion_metrics(
                previous_measurements=(
                    previous_measurements
                ),
                current_measurements=(
                    measurements
                ),
            )
        )

        measurements[
            'motion_metrics'
        ] = motion

        moment.measurements = (
            measurements
        )

        moment.save(
            update_fields=[
                'measurements',
                'updated_at',
            ],
        )

        previous_measurements = (
            measurements
        )

        processed += 1


    return {
        'frames_with_motion_metrics': (
            processed
        ),
    }