from video_library.models import (
    VideoAnalysis,
)

from .frame_service import (
    extract_analysis_frames,
)

from .phase_service import (
    detect_analysis_phases,
)

from .pose_overlay_service import (
    generate_pose_overlay_frames,
)

from .pose_service import (
    analyze_extracted_frames,
)

from .skill_analysis_service import (
    generate_skill_observations,
)

from .key_frame_service import (
    select_key_frames,
)
from .motion_service import (
    calculate_analysis_motion,
)



class ComputerVisionPipelineError(
    Exception
):
    pass


class ComputerVisionPipeline:
    """
    Run the complete computer-vision pipeline
    for one VideoAnalysis.

    Current stages:

    1. Extract real video frames with OpenCV.
    2. Detect body landmarks with MediaPipe.
    3. Calculate real joint angles.
    4. Generate gymnastics-specific measurements.
    5. Detect broad movement phases.
    6. Apply skill-specific analysis rules.
    7. Generate annotated pose overlays.
    """

    def __init__(
            self,
            sample_count=None,
    ):
        self.sample_count = (
            sample_count
        )


    def process(
        self,
        analysis: VideoAnalysis,
    ):
        results = {
            'frames_extracted': 0,
            'frames_analyzed': 0,
            'poses_detected': 0,
            'phases_classified': 0,
            'skill_observations_created': 0,
            'overlays_generated': 0,
        }


        try:

            #
            # STEP 1
            # Extract real video frames.
            #
            analysis.update_progress(
                percentage=20,
                step=(
                    'Extracting real '
                    'video frames'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_PROCESSING
                ),
            )


            frames = (
                extract_analysis_frames(
                    analysis=analysis,
                    sample_count=(
                        self.sample_count
                    ),
                )
            )


            results[
                'frames_extracted'
            ] = len(
                frames
            )


            #
            # STEP 2
            # MediaPipe pose detection.
            #
            analysis.update_progress(
                percentage=40,
                step=(
                    'Detecting athlete '
                    'body landmarks'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_PROCESSING
                ),
            )


            pose_results = (
                analyze_extracted_frames(
                    analysis
                )
            )


            results[
                'frames_analyzed'
            ] = pose_results[
                'analyzed_frames'
            ]


            results[
                'poses_detected'
            ] = pose_results[
                'frames_with_pose'
            ]


            #
            # STEP 3
            # Joint angles and gymnastics
            # measurements are calculated
            # inside analyze_extracted_frames().
            #
            analysis.update_progress(
                percentage=60,
                step=(
                    'Calculating joint angles '
                    'and gymnastics measurements'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_PROCESSING
                ),
            )

            analysis.update_progress(
                percentage=67,
                step='Analyzing movement between frames',
                status=(
                    VideoAnalysis.STATUS_PROCESSING
                ),
            )

            motion_results = (
                calculate_analysis_motion(
                    analysis
                )
            )

            results[
                'frames_with_motion_metrics'
            ] = motion_results[
                'frames_with_motion_metrics'
            ]
            #
            # STEP 4
            # Detect movement phases.
            #
            analysis.update_progress(
                percentage=72,
                step=(
                    'Detecting movement phases'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_PROCESSING
                ),
            )


            phase_results = (
                detect_analysis_phases(
                    analysis
                )
            )


            results[
                'phases_classified'
            ] = phase_results[
                'classified_frames'
            ]

            analysis.update_progress(
                percentage=78,
                step='Selecting key analysis frames',
                status=(
                    VideoAnalysis.STATUS_PROCESSING
                ),
            )

            key_frame_results = (
                select_key_frames(
                    analysis=analysis,
                    maximum_key_frames=8,
                )
            )

            results[
                'frames_scored'
            ] = key_frame_results[
                'frames_scored'
            ]

            results[
                'key_frames_selected'
            ] = key_frame_results[
                'key_frames_selected'
            ]




            #
            # STEP 5
            # Apply skill-specific rules.
            #
            analysis.update_progress(
                percentage=92,
                step=(
                    'Applying skill-specific '
                    'analysis rules'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_PROCESSING
                ),
            )


            skill_results = (
                generate_skill_observations(
                    analysis
                )
            )


            results[
                'skill_observations_created'
            ] = skill_results[
                'observations_created'
            ]


            results[
                'skill_rule_set_found'
            ] = skill_results[
                'rule_set_found'
            ]


            results[
                'skill_name'
            ] = skill_results[
                'skill'
            ]


            #
            # STEP 6
            # Generate annotated overlays.
            #
            analysis.update_progress(
                percentage=90,
                step=(
                    'Generating pose overlays'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_GENERATING_RESULTS
                ),
            )


            overlay_results = (
                generate_pose_overlay_frames(
                    analysis
                )
            )


            results[
                'overlays_generated'
            ] = overlay_results[
                'generated_frames'
            ]


            #
            # STEP 7
            # Finalize CV results.
            #
            analysis.update_progress(
                percentage=96,
                step=(
                    'Finalizing computer '
                    'vision results'
                ),
                status=(
                    VideoAnalysis
                    .STATUS_GENERATING_RESULTS
                ),
            )


            return results


        except Exception as error:

            raise ComputerVisionPipelineError(
                str(
                    error
                )
            ) from error