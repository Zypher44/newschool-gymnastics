import tempfile
import uuid
from pathlib import Path

from django.core.files import File

from video_library.models import VideoAnalysis

from .storage_files import local_storage_file


def generate_pose_overlay_frames(
    analysis: VideoAnalysis,
):
    """
    Generate annotated copies of extracted frames.

    The original frame_image is preserved.
    The annotated version is stored separately in
    annotated_frame_image.
    """

    generated_count = 0

    moments = (
        analysis.moments
        .exclude(
            frame_image='',
        )
        .order_by(
            'timestamp_seconds',
        )
    )

    with tempfile.TemporaryDirectory() as temp_directory:
        temp_directory = Path(
            temp_directory
        )

        for moment in moments:
            measurements = (
                moment.measurements
                or {}
            )

            landmarks = measurements.get(
                'pose_landmarks'
            )

            if not landmarks:
                continue

            pose_angles = (
                measurements.get(
                    'pose_angles'
                )
                or {}
            )

            unique_name = (
                f'pose_overlay_'
                f'{moment.id}_'
                f'{uuid.uuid4().hex[:8]}.jpg'
            )

            output_path = (
                temp_directory
                / unique_name
            )

            from .pose_drawing import draw_pose_overlay
            with local_storage_file(moment.frame_image, maximum_bytes=25 * 1024 * 1024) as original_path:
                draw_pose_overlay(
                    image_path=original_path,
                    output_path=output_path,
                    landmarks=landmarks,
                    pose_angles=pose_angles,
                )

            if not output_path.exists():
                raise ValueError(
                    (
                        'Overlay file was not created: '
                        f'{output_path}'
                    )
                )

            if moment.annotated_frame_image:
                moment.annotated_frame_image.delete(save=False)

            with output_path.open(
                'rb'
            ) as annotated_file:
                moment.annotated_frame_image.save(
                    unique_name,
                    File(
                        annotated_file
                    ),
                    save=False,
                )

            measurements[
                'pose_overlay_generated'
            ] = True

            measurements[
                'pose_overlay_filename'
            ] = unique_name

            moment.measurements = measurements

            moment.save(
                update_fields=[
                    'annotated_frame_image',
                    'measurements',
                    'updated_at',
                ],
            )

            generated_count += 1

    return {
        'generated_frames': generated_count,
    }