from pathlib import Path
import tempfile

import cv2

from django.core.files import File


class ThumbnailGenerationError(
    Exception
):
    pass


def generate_video_thumbnail(
    video,
):
    """
    Generate a representative JPEG thumbnail
    from an uploaded video and save it to
    video.thumbnail.
    """

    if not video.video_file:
        raise ThumbnailGenerationError(
            'Video file is missing.'
        )


    video_path = Path(
        video.video_file.path
    )


    if not video_path.exists():
        raise ThumbnailGenerationError(
            (
                'Video file does not exist: '
                f'{video_path}'
            )
        )


    capture = cv2.VideoCapture(
        str(
            video_path
        )
    )


    if not capture.isOpened():
        raise ThumbnailGenerationError(
            'OpenCV could not open the video.'
        )


    try:
        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
            or 0
        )

        fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
            or 0.0
        )


        #
        # Try to use a frame around 15% into
        # the video instead of the first frame.
        #
        if frame_count > 0:
            target_frame = int(
                frame_count
                * 0.15
            )

        else:
            target_frame = 0


        capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            target_frame,
        )


        success, frame = (
            capture.read()
        )


        #
        # Fall back to the first frame if the
        # preferred frame could not be read.
        #
        if not success:

            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                0,
            )

            success, frame = (
                capture.read()
            )


        if not success:
            raise ThumbnailGenerationError(
                (
                    'OpenCV could not read '
                    'a usable video frame.'
                )
            )


        #
        # Resize very large frames so thumbnails
        # stay lightweight.
        #
        height, width = (
            frame.shape[:2]
        )

        maximum_width = 1280


        if width > maximum_width:

            scale = (
                maximum_width
                / width
            )

            resized_width = int(
                width
                * scale
            )

            resized_height = int(
                height
                * scale
            )


            frame = cv2.resize(
                frame,
                (
                    resized_width,
                    resized_height,
                ),
                interpolation=(
                    cv2.INTER_AREA
                ),
            )


        with tempfile.TemporaryDirectory() as temp_directory:

            temp_directory = Path(
                temp_directory
            )


            thumbnail_name = (
                f'video_'
                f'{video.id}_'
                f'thumbnail.jpg'
            )


            thumbnail_path = (
                temp_directory
                / thumbnail_name
            )


            saved = cv2.imwrite(
                str(
                    thumbnail_path
                ),
                frame,
                [
                    int(
                        cv2.IMWRITE_JPEG_QUALITY
                    ),
                    88,
                ],
            )


            if not saved:
                raise ThumbnailGenerationError(
                    (
                        'OpenCV could not save '
                        'the thumbnail image.'
                    )
                )


            with thumbnail_path.open(
                'rb'
            ) as thumbnail_file:

                video.thumbnail.save(
                    thumbnail_name,
                    File(
                        thumbnail_file
                    ),
                    save=False,
                )


            video.save(
                update_fields=[
                    'thumbnail',
                ],
            )


    finally:

        capture.release()


    return video.thumbnail