from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mediapipe as mp


MODEL_PATH = (
    Path(__file__).resolve().parent
    / 'models'
    / 'pose_landmarker_full.task'
)


class PoseDetectionError(Exception):
    pass


@dataclass
class PoseLandmarkResult:
    index: int
    name: str
    x: float
    y: float
    z: float
    visibility: float | None
    presence: float | None


@dataclass
class PoseResult:
    detected: bool
    landmarks: list[PoseLandmarkResult]
    landmark_count: int
    metadata: dict[str, Any]


POSE_LANDMARK_NAMES = [
    'nose',
    'left_eye_inner',
    'left_eye',
    'left_eye_outer',
    'right_eye_inner',
    'right_eye',
    'right_eye_outer',
    'left_ear',
    'right_ear',
    'mouth_left',
    'mouth_right',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'left_pinky',
    'right_pinky',
    'left_index',
    'right_index',
    'left_thumb',
    'right_thumb',
    'left_hip',
    'right_hip',
    'left_knee',
    'right_knee',
    'left_ankle',
    'right_ankle',
    'left_heel',
    'right_heel',
    'left_foot_index',
    'right_foot_index',
]


class MediaPipePoseEngine:
    def __init__(
        self,
        model_path: str | Path | None = None,
    ):
        self.model_path = Path(
            model_path or MODEL_PATH
        )

        if not self.model_path.exists():
            raise PoseDetectionError(
                (
                    'Pose model file was not found: '
                    f'{self.model_path}'
                )
            )

        base_options = mp.tasks.BaseOptions(
            model_asset_path=str(
                self.model_path
            )
        )

        options = (
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=(
                    mp.tasks.vision.RunningMode.IMAGE
                ),
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_segmentation_masks=False,
            )
        )

        self.landmarker = (
            mp.tasks.vision.PoseLandmarker
            .create_from_options(
                options
            )
        )

    def close(self):
        if self.landmarker:
            self.landmarker.close()

    def analyze_image(
        self,
        image_path: str | Path,
    ) -> PoseResult:
        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise PoseDetectionError(
                (
                    'Image file does not exist: '
                    f'{image_path}'
                )
            )

        image = mp.Image.create_from_file(
            str(image_path)
        )

        result = self.landmarker.detect(
            image
        )

        if not result.pose_landmarks:
            return PoseResult(
                detected=False,
                landmarks=[],
                landmark_count=0,
                metadata={
                    'engine': 'MediaPipePoseEngine',
                    'model': self.model_path.name,
                },
            )

        detected_pose = (
            result.pose_landmarks[0]
        )

        landmarks = []

        for index, landmark in enumerate(
            detected_pose
        ):
            if index < len(
                POSE_LANDMARK_NAMES
            ):
                name = (
                    POSE_LANDMARK_NAMES[index]
                )
            else:
                name = f'landmark_{index}'

            landmarks.append(
                PoseLandmarkResult(
                    index=index,
                    name=name,
                    x=float(
                        landmark.x
                    ),
                    y=float(
                        landmark.y
                    ),
                    z=float(
                        landmark.z
                    ),
                    visibility=(
                        float(
                            landmark.visibility
                        )
                        if landmark.visibility
                        is not None
                        else None
                    ),
                    presence=(
                        float(
                            landmark.presence
                        )
                        if landmark.presence
                        is not None
                        else None
                    ),
                )
            )

        return PoseResult(
            detected=True,
            landmarks=landmarks,
            landmark_count=len(
                landmarks
            ),
            metadata={
                'engine': 'MediaPipePoseEngine',
                'model': self.model_path.name,
            },
        )