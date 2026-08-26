import tempfile
from pathlib import Path

from django.core.files import File

from video_library.models import (
    VideoAnalysis,
    VideoAnalysisMoment,
)

from .frame_extraction import (
    extract_sample_frames,
)
from .video_processing import (
    read_video_metadata,
)
from .frame_extraction import (
    calculate_dynamic_sample_count,
    extract_sample_frames,
)

def extract_analysis_frames(
    analysis: VideoAnalysis,
    sample_count: int | None = None,
):
    """
    Extract real sample frames from a video's file and store
    them as analysis moments.

    This is not pose detection yet.
    """

    video = analysis.video

    if not video.video_file:
        raise ValueError(
            'This video does not have a source file.'
        )

    video_path = Path(
        video.video_file.path
    )

    metadata = read_video_metadata(
        str(video_path)
    )

    if sample_count is None:
        sample_count = (
            calculate_dynamic_sample_count(
                duration_seconds=(
                    metadata.duration_seconds
                ),
                fps=metadata.fps,
            )
        )

    if metadata.duration_seconds <= 0:
        raise ValueError(
            'Video duration could not be determined.'
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        extracted_frames = extract_sample_frames(
            video_path=str(video_path),
            output_directory=temp_directory,
            duration_seconds=metadata.duration_seconds,
            sample_count=sample_count,
        )

        existing_frames = (
            analysis.moments
            .filter(
                moment_type=(
                    VideoAnalysisMoment.MOMENT_OBSERVATION
                ),
                label__startswith='Extracted Frame',
            )
        )

        for existing_moment in existing_frames:
            if existing_moment.frame_image:
                existing_moment.frame_image.delete(
                    save=False
                )

            if existing_moment.annotated_frame_image:
                existing_moment.annotated_frame_image.delete(
                    save=False
                )

        existing_frames.delete()

        saved_moments = []

        for index, extracted_frame in enumerate(
            extracted_frames,
            start=1,
        ):
            moment = VideoAnalysisMoment.objects.create(
                analysis=analysis,
                timestamp_seconds=(
                    extracted_frame.timestamp_seconds
                ),
                moment_type=(
                    VideoAnalysisMoment.MOMENT_OBSERVATION
                ),
                label=f'Extracted Frame {index}',
                description=(
                    'Real frame extracted from the uploaded '
                    'video for future pose analysis.'
                ),
                severity=(
                    VideoAnalysisMoment.SEVERITY_INFO
                ),
                measurements={
                    'frame_number': (
                        extracted_frame.frame_number
                    ),
                    'source': 'opencv',
                    'real_frame': True,
                },
                display_order=100 + index,
            )

            frame_path = Path(
                extracted_frame.output_path
            )

            with frame_path.open(
                'rb'
            ) as image_file:
                moment.frame_image.save(
                    frame_path.name,
                    File(
                        image_file
                    ),
                    save=True,
                )

            saved_moments.append(
                moment
            )

    return saved_moments