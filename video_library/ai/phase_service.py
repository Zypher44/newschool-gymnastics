from video_library.models import (
    VideoAnalysis,
)

from .skill_phases import (
    classify_frame_phase,
)


def detect_analysis_phases(
    analysis: VideoAnalysis,
):
    """
    Classify extracted analysis frames into broad
    gymnastics movement phases.

    The classifier receives the current skill name so
    skill-specific phase logic can be applied when available.
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


    total_frames = len(
        moments
    )


    #
    # ---------------------------------------------------------
    # DETERMINE SKILL NAME
    # ---------------------------------------------------------
    #
    # Prefer the skill explicitly requested for this analysis.
    #
    # If unavailable, fall back to:
    #
    # 1. detected skill
    # 2. skill stored on the video
    #

    skill_name = (
        analysis.requested_skill
        or analysis.detected_skill
        or analysis.video.skill_name
        or ''
    ).strip()


    print(
        'PHASE DETECTION SKILL:',
        repr(
            skill_name
        ),
    )


    results = []


    for index, moment in enumerate(
        moments
    ):

        measurements = (
            moment.measurements
            or {}
        )


        gymnastics_measurements = (
            measurements.get(
                'gymnastics_measurements'
            )
            or {}
        )


        motion_metrics = (
            measurements.get(
                'motion_metrics'
            )
            or {}
        )


        #
        # -----------------------------------------------------
        # CLASSIFY PHASE
        # -----------------------------------------------------
        #

        result = (
            classify_frame_phase(
                frame_index=index,

                total_frames=(
                    total_frames
                ),

                gymnastics_measurements=(
                    gymnastics_measurements
                ),

                motion_metrics=(
                    motion_metrics
                ),

                skill_name=(
                    skill_name
                ),
            )
        )


        #
        # -----------------------------------------------------
        # SAVE RESULT
        # -----------------------------------------------------
        #

        measurements[
            'skill_phase'
        ] = result.phase


        measurements[
            'skill_phase_confidence'
        ] = round(
            result.confidence,
            3,
        )


        measurements[
            'skill_phase_reason'
        ] = (
            result.reason
        )


        #
        # Helpful metadata so we can later see which
        # skill was used by the phase classifier.
        #
        measurements[
            'skill_phase_skill'
        ] = (
            skill_name
        )


        moment.measurements = (
            measurements
        )


        moment.save(
            update_fields=[
                'measurements',
                'updated_at',
            ],
        )


        results.append({

            'moment_id': (
                moment.id
            ),

            'frame_index': (
                index
            ),

            'timestamp_seconds': (
                float(
                    moment.timestamp_seconds
                )
            ),

            'phase': (
                result.phase
            ),

            'confidence': (
                result.confidence
            ),

            'skill_name': (
                skill_name
            ),
        })


    return {

        'classified_frames': len(
            results
        ),

        'skill_name': (
            skill_name
        ),

        'results': (
            results
        ),
    }