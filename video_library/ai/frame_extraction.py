from dataclasses import dataclass
from pathlib import Path

import cv2


class FrameExtractionError(Exception):
    pass


@dataclass
class ExtractedFrame:
    timestamp_seconds: float
    frame_number: int
    output_path: str

def calculate_dynamic_sample_count(
    *,
    duration_seconds: float,
    fps: float,
    minimum_samples: int = 8,
    maximum_samples: int = 60,
    samples_per_second: float = 2.0,
) -> int:
    """
    Decide how many frames should be sampled from a video.

    The current strategy targets roughly two samples per
    second while keeping processing within safe limits.
    """

    if duration_seconds <= 0:
        return minimum_samples

    estimated_samples = int(
        round(
            duration_seconds
            * samples_per_second
        )
    )

    #
    # Very high-FPS videos may contain fast gymnastics
    # movement, so allow a modest sampling increase.
    #
    if fps >= 50:
        estimated_samples = int(
            round(
                estimated_samples
                * 1.25
            )
        )

    return max(
        minimum_samples,
        min(
            maximum_samples,
            estimated_samples,
        ),
    )


def extract_frame_at_timestamp(
    video_path: str,
    output_path: str,
    timestamp_seconds: float,
) -> ExtractedFrame:
    """
    Extract one real frame from a video at the requested timestamp.
    """

    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FrameExtractionError(
            f'Video file does not exist: {video_path}'
        )

    capture = cv2.VideoCapture(
        str(video_path)
    )

    if not capture.isOpened():
        raise FrameExtractionError(
            'OpenCV could not open the video.'
        )

    try:
        fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        if fps <= 0:
            raise FrameExtractionError(
                'Video FPS could not be determined.'
            )

        capture.set(
            cv2.CAP_PROP_POS_MSEC,
            float(timestamp_seconds) * 1000,
        )

        success, frame = capture.read()

        if not success or frame is None:
            raise FrameExtractionError(
                (
                    'Unable to read a frame at '
                    f'{timestamp_seconds:.3f} seconds.'
                )
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
            raise FrameExtractionError(
                'OpenCV could not save the extracted frame.'
            )

        frame_number = int(
            round(
                timestamp_seconds * fps
            )
        )

        return ExtractedFrame(
            timestamp_seconds=timestamp_seconds,
            frame_number=frame_number,
            output_path=str(output_path),
        )

    finally:
        capture.release()


def build_sample_timestamps(
    duration_seconds: float,
    sample_count: int = 6,
) -> list[float]:
    """
    Build evenly spaced timestamps across the useful portion
    of a video.

    We avoid the exact first and last frames because they are
    often less useful.
    """

    if duration_seconds <= 0:
        return []

    if sample_count <= 0:
        return []

    start = min(
        0.15,
        duration_seconds * 0.05,
    )

    end = max(
        duration_seconds - 0.15,
        start,
    )

    if sample_count == 1:
        return [
            round(
                duration_seconds / 2,
                3,
            )
        ]

    if end <= start:
        return [
            round(
                duration_seconds / 2,
                3,
            )
        ]

    step = (
        end - start
    ) / (
        sample_count - 1
    )

    timestamps = []

    for index in range(
        sample_count
    ):
        timestamp = (
            start
            + step * index
        )

        timestamps.append(
            round(
                timestamp,
                3,
            )
        )

    return timestamps

def extract_sample_frames(
    video_path: str,
    output_directory: str,
    duration_seconds: float,
    sample_count: int = 6,
) -> list[ExtractedFrame]:
    """
    Extract a set of evenly spaced real frames from a video.
    """

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamps = build_sample_timestamps(
        duration_seconds=duration_seconds,
        sample_count=sample_count,
    )

    extracted_frames = []

    for index, timestamp in enumerate(
        timestamps,
        start=1,
    ):
        output_path = (
            output_directory
            / f'frame_{index:02d}.jpg'
        )

        frame = extract_frame_at_timestamp(
            video_path=video_path,
            output_path=str(output_path),
            timestamp_seconds=timestamp,
        )

        extracted_frames.append(
            frame
        )

    return extracted_frames
