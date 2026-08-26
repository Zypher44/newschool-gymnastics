from decimal import Decimal
from pathlib import Path

from django.core.files import File

from .video_processing import (
    extract_thumbnail,
    read_video_metadata,
)


def process_video_file(
    video,
):
    """
    Read real video metadata and create a thumbnail.

    This currently expects local Django FileSystemStorage.
    Later, we can adapt this service for object storage.
    """

    if not video.video_file:
        raise ValueError(
            'Video does not have a file.'
        )

    video_path = Path(
        video.video_file.path
    )

    metadata = read_video_metadata(
        str(video_path)
    )

    video.duration_seconds = int(
        round(
            metadata.duration_seconds
        )
    )

    video.video_fps = Decimal(
        str(
            round(
                metadata.fps,
                3,
            )
        )
    )

    video.frame_count = (
        metadata.frame_count
    )

    video.video_width = (
        metadata.width
    )

    video.video_height = (
        metadata.height
    )

    thumbnail_path = (
        video_path.parent
        / (
            f'{video_path.stem}'
            f'_thumbnail.jpg'
        )
    )

    extract_thumbnail(
        video_path=str(
            video_path
        ),
        output_path=str(
            thumbnail_path
        ),
    )

    with thumbnail_path.open(
        'rb'
    ) as thumbnail_file:
        video.thumbnail.save(
            thumbnail_path.name,
            File(
                thumbnail_file
            ),
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

    try:
        thumbnail_path.unlink()
    except OSError:
        pass

    return metadata