from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2


@dataclass
class VideoMetadata:
    fps: float
    frame_count: int
    duration_seconds: float
    width: int
    height: int


class VideoProcessingError(Exception):
    pass


def read_video_metadata(
    video_path: str,
) -> VideoMetadata:
    """
    Read real metadata from a video using OpenCV.
    """

    path = Path(video_path)

    if not path.exists():
        raise VideoProcessingError(
            f'Video file does not exist: {video_path}'
        )

    capture = cv2.VideoCapture(
        str(path)
    )

    if not capture.isOpened():
        raise VideoProcessingError(
            'OpenCV could not open the video.'
        )

    try:
        fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        width = int(
            capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        height = int(
            capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        if fps > 0:
            duration_seconds = (
                frame_count / fps
            )
        else:
            duration_seconds = 0.0

        return VideoMetadata(
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
        )

    finally:
        capture.release()


def extract_thumbnail(
    video_path: str,
    output_path: str,
    timestamp_seconds: Optional[float] = None,
) -> str:
    """
    Extract one frame from the video and save it as a JPEG.
    """

    video_path = Path(
        video_path
    )

    output_path = Path(
        output_path
    )

    if not video_path.exists():
        raise VideoProcessingError(
            'Video file does not exist.'
        )

    capture = cv2.VideoCapture(
        str(video_path)
    )

    if not capture.isOpened():
        raise VideoProcessingError(
            'OpenCV could not open the video.'
        )

    try:
        fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        if timestamp_seconds is None:
            if fps > 0 and frame_count > 0:
                duration = (
                    frame_count / fps
                )

                timestamp_seconds = min(
                    max(
                        duration * 0.25,
                        0.1,
                    ),
                    max(
                        duration - 0.1,
                        0.1,
                    ),
                )
            else:
                timestamp_seconds = 0.0

        capture.set(
            cv2.CAP_PROP_POS_MSEC,
            float(timestamp_seconds) * 1000,
        )

        success, frame = capture.read()

        if not success or frame is None:
            raise VideoProcessingError(
                'Unable to extract thumbnail frame.'
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved = cv2.imwrite(
            str(output_path),
            frame,
        )

        if not saved:
            raise VideoProcessingError(
                'Unable to save thumbnail image.'
            )

        return str(
            output_path
        )

    finally:
        capture.release()