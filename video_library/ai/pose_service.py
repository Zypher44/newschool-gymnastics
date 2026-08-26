from pathlib import Path

from video_library.models import (
    VideoAnalysis,
)

from .pose import MediaPipePoseEngine
from .measurements import (
    calculate_pose_angles,
)

from .gymnastics_measurements import (
    calculate_gymnastics_measurements,
)


IMPORTANT_LANDMARKS = {
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'left_hip',
    'right_hip',
    'left_knee',
    'right_knee',
    'left_ankle',
    'right_ankle',
}


def analyze_extracted_frames(
    analysis: VideoAnalysis,
):
    """
    Run real MediaPipe pose detection on extracted
    analysis frames.

    Pose coordinates are stored inside each moment's
    measurements JSON.
    """

    engine = MediaPipePoseEngine()

    analyzed_count = 0
    detected_count = 0

    try:
        moments = (
            analysis.moments
            .exclude(
                frame_image='',
            )
            .order_by(
                'timestamp_seconds',
            )
        )

        for moment in moments:
            if not moment.frame_image:
                continue

            image_path = Path(
                moment.frame_image.path
            )

            result = engine.analyze_image(
                image_path
            )

            analyzed_count += 1

            measurements = dict(
                moment.measurements
                or {}
            )

            measurements[
                'pose_engine'
            ] = 'mediapipe'

            measurements[
                'pose_detected'
            ] = result.detected

            measurements[
                'pose_landmark_count'
            ] = result.landmark_count

            if result.detected:
                detected_count += 1

                measurements[
                    'pose_landmarks'
                ] = {
                    landmark.name: {
                        'x': round(
                            landmark.x,
                            6,
                        ),
                        'y': round(
                            landmark.y,
                            6,
                        ),
                        'z': round(
                            landmark.z,
                            6,
                        ),
                        'visibility': (
                            round(
                                landmark.visibility,
                                6,
                            )
                            if landmark.visibility
                            is not None
                            else None
                        ),
                    }
                    for landmark
                    in result.landmarks
                    if landmark.name
                    in IMPORTANT_LANDMARKS
                }

            moment.measurements = (
                measurements
            )

            pose_landmarks = (
                    measurements.get(
                        'pose_landmarks'
                    )
                    or {}
            )

            if pose_landmarks:

                pose_angles = (
                    calculate_pose_angles(
                        pose_landmarks
                    )
                )

                measurements[
                    'pose_angles'
                ] = pose_angles

                gymnastics_measurements = (
                    calculate_gymnastics_measurements(
                        landmarks=pose_landmarks,
                        pose_angles=pose_angles,
                    )
                )

                measurements[
                    'gymnastics_measurements'
                ] = gymnastics_measurements


            else:

                measurements[
                    'pose_angles'
                ] = {}

                measurements[
                    'gymnastics_measurements'
                ] = {}

            measurements[
                'gymnastics_measurements'
            ] = (
                gymnastics_measurements
            )

            moment.save(
                update_fields=[
                    'measurements',
                    'updated_at',
                ],
            )

    finally:
        engine.close()

    return {
        'analyzed_frames': analyzed_count,
        'frames_with_pose': detected_count,
    }