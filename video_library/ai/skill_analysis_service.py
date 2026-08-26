from video_library.models import (
    VideoAnalysis,
    VideoAnalysisMoment,
)

from .skill_rules import (
    get_rule_set,
)


def generate_skill_observations(
    analysis: VideoAnalysis,
):
    skill_name = (
        analysis.detected_skill
        or analysis.requested_skill
        or analysis.video.skill_name
        or ''
    )

    rule_set = get_rule_set(
        skill_name
    )

    if not rule_set:
        return {
            'skill': skill_name,
            'rule_set_found': False,
            'observations_created': 0,
        }

    frame_moments = list(
        analysis.moments
        .exclude(
            frame_image='',
        )
        .order_by(
            'timestamp_seconds',
        )
    )

    created = 0


    analysis.moments.filter(
        label__startswith='Skill Observation:'
    ).delete()


    for frame_moment in frame_moments:

        measurements = (
            frame_moment.measurements
            or {}
        )

        phase = (
            measurements.get(
                'skill_phase'
            )
        )

        if not phase:
            continue

        quality = (
            rule_set.get_analysis_quality(
                measurements
            )
        )

        measurements[
            'analysis_quality'
        ] = quality

        frame_moment.measurements = (
            measurements
        )

        frame_moment.save(
            update_fields=[
                'measurements',
                'updated_at',
            ],
        )

        observations = (
            rule_set.evaluate_frame(
                phase=phase,
                measurements=measurements,
            )
        )

        for observation in observations:

            VideoAnalysisMoment.objects.create(
                analysis=analysis,
                timestamp_seconds=(
                    frame_moment.timestamp_seconds
                ),
                moment_type=(
                    VideoAnalysisMoment
                    .MOMENT_OBSERVATION
                ),
                label=(
                    'Skill Observation: '
                    f'{observation.title}'
                ),
                description=(
                    observation.description
                ),
                severity=(
                    observation.severity
                ),
                confidence=(
                    observation.confidence
                ),
                measurements={
                    'skill_specific': True,

                    'skill_name': (
                        skill_name
                    ),

                    'skill_phase': (
                        observation.phase
                    ),

                    'observation_code': (
                        observation.code
                    ),

                    'source_frame_moment_id': (
                        frame_moment.id
                    ),

                    'observation_measurements': (
                        observation.measurements
                    ),

                    'evidence': (
                        observation.evidence
                    ),

                    'observation_confidence': (
                        observation.confidence
                    ),

                    'rule_version': (
                        observation.rule_version
                    ),

                    'source_frame_number': (
                        measurements.get(
                            'frame_number'
                        )
                    ),

                    'source_timestamp_seconds': (
                        float(
                            frame_moment
                            .timestamp_seconds
                        )
                    ),
                },
                display_order=(
                    500 + created
                ),
            )

            created += 1

    return {
        'skill': skill_name,
        'rule_set_found': True,
        'observations_created': created,
    }