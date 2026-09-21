from decimal import Decimal
from pathlib import Path
import tempfile

from django.core.files import File

from .video_processing import (
    extract_thumbnail,
    read_video_metadata,
)


def process_video_file(video):
    """Read metadata and create a thumbnail from local or cloud storage."""

    if not video.video_file:
        raise ValueError('Video does not have a file.')

    video_extension = (
        Path(video.video_file.name).suffix.lower()
        or '.mp4'
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_directory = Path(temporary_directory)
        video_path = temporary_directory / f'source{video_extension}'
        thumbnail_path = temporary_directory / 'thumbnail.jpg'

        try:
            video.video_file.open('rb')

            with video_path.open('wb') as local_file:
                for chunk in iter(
                    lambda: video.video_file.read(1024 * 1024),
                    b'',
                ):
                    local_file.write(chunk)

        finally:
            video.video_file.close()

        metadata = read_video_metadata(str(video_path))

        video.duration_seconds = int(round(metadata.duration_seconds))
        video.video_fps = Decimal(str(round(metadata.fps, 3)))
        video.frame_count = metadata.frame_count
        video.video_width = metadata.width
        video.video_height = metadata.height

        extract_thumbnail(
            video_path=str(video_path),
            output_path=str(thumbnail_path),
        )

        with thumbnail_path.open('rb') as thumbnail_file:
            video.thumbnail.save(
                f'video_{video.id}_thumbnail.jpg',
                File(thumbnail_file),
                save=False,
            )

        video.save(
            update_fields=[
                'duration_seconds',
                'video_fps',
                'frame_count',
                'video_width',
                'video_height',
                'thumbnail',
                'updated_at',
            ],
        )

    return metadata
