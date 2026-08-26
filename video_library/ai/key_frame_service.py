from video_library.models import (
    VideoAnalysis,
)

from .frame_scoring import (
    calculate_frame_score,
)


PHASE_PRIORITY = [
    'setup',
    'entry',
    'main_action',
    'peak',
    'exit',
    'finish',
]


def select_key_frames(
    analysis: VideoAnalysis,
    maximum_key_frames: int = 8,
):
    """
    Score all analyzed frames and select a diverse,
    motion-aware set of key frames.

    Selection strategy:

    1. Best frame from each detected phase.
    2. Strong stable peak candidate.
    3. Highest movement-change frames.
    4. Fill remaining slots by overall frame score.
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

    scored_moments = []


    #
    # Score every frame.
    #
    for moment in moments:

        measurements = dict(
            moment.measurements
            or {}
        )

        score_result = (
            calculate_frame_score(
                measurements
            )
        )

        motion = (
            measurements.get(
                'motion_metrics'
            )
            or {}
        )

        movement_score = float(
            motion.get(
                'movement_score'
            )
            or 0.0
        )

        phase = (
            measurements.get(
                'skill_phase'
            )
            or 'unknown'
        )


        measurements[
            'frame_quality_score'
        ] = score_result[
            'score'
        ]

        measurements[
            'frame_quality_reasons'
        ] = score_result[
            'reasons'
        ]

        measurements[
            'is_key_frame'
        ] = False

        measurements[
            'key_frame_reason'
        ] = None


        moment.measurements = (
            measurements
        )

        moment.save(
            update_fields=[
                'measurements',
                'updated_at',
            ],
        )


        scored_moments.append(
            {
                'moment': moment,
                'score': (
                    score_result[
                        'score'
                    ]
                ),
                'phase': phase,
                'movement_score': (
                    movement_score
                ),
            }
        )


    selected = []
    selected_ids = set()


    def add_selected(
        item,
        reason,
    ):
        if not item:
            return

        moment = item[
            'moment'
        ]

        if moment.id in selected_ids:
            return

        if (
            len(selected)
            >= maximum_key_frames
        ):
            return

        selected.append(
            item
        )

        selected_ids.add(
            moment.id
        )

        measurements = dict(
            moment.measurements
            or {}
        )

        measurements[
            'is_key_frame'
        ] = True

        measurements[
            'key_frame_reason'
        ] = reason

        moment.measurements = (
            measurements
        )

        moment.save(
            update_fields=[
                'measurements',
                'updated_at',
            ],
        )


    #
    # ---------------------------------------------------------
    # 1. BEST FRAME PER PHASE
    # ---------------------------------------------------------
    #

    for phase in PHASE_PRIORITY:

        phase_items = [
            item
            for item in scored_moments
            if item[
                'phase'
            ] == phase
        ]

        if not phase_items:
            continue

        best_phase_frame = max(
            phase_items,
            key=lambda item: (
                item[
                    'score'
                ]
            ),
        )

        add_selected(
            best_phase_frame,
            (
                'Best quality frame '
                f'for {phase.replace("_", " ")} phase.'
            ),
        )


    #
    # ---------------------------------------------------------
    # 2. STABLE PEAK
    # ---------------------------------------------------------
    #

    peak_candidates = [
        item
        for item in scored_moments
        if (
            item[
                'phase'
            ] == 'peak'
            and item[
                'movement_score'
            ] < 8
        )
    ]

    if peak_candidates:

        stable_peak = max(
            peak_candidates,
            key=lambda item: (
                item[
                    'score'
                ]
            ),
        )

        add_selected(
            stable_peak,
            'Strong stable peak-position frame.',
        )


    #
    # ---------------------------------------------------------
    # 3. HIGHEST MOVEMENT FRAMES
    # ---------------------------------------------------------
    #

    motion_candidates = sorted(
        scored_moments,
        key=lambda item: (
            item[
                'movement_score'
            ]
        ),
        reverse=True,
    )


    for item in motion_candidates:

        if (
            len(selected)
            >= maximum_key_frames
        ):
            break

        if (
            item[
                'movement_score'
            ] <= 0
        ):
            continue

        add_selected(
            item,
            (
                'High movement-change frame '
                f'({item["movement_score"]:.1f}).'
            ),
        )


    #
    # ---------------------------------------------------------
    # 4. FILL REMAINING SLOTS BY FRAME SCORE
    # ---------------------------------------------------------
    #

    overall_candidates = sorted(
        scored_moments,
        key=lambda item: (
            item[
                'score'
            ]
        ),
        reverse=True,
    )


    for item in overall_candidates:

        if (
            len(selected)
            >= maximum_key_frames
        ):
            break

        add_selected(
            item,
            'High overall analysis quality.',
        )


    return {
        'frames_scored': len(
            scored_moments
        ),

        'key_frames_selected': len(
            selected
        ),
    }