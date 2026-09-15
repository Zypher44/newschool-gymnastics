from pathlib import Path
import tempfile

import cv2

from django.core.files import File


class ThumbnailGenerationError(
    Exception
):
    pass


def generate_video_thumbnail(video):
    """
    Generate a thumbnail from either local storage or cloud storage.
    """

    if not video.video_file:
        raise ThumbnailGenerationError(
            "Video file is missing."
        )

    video_extension = (
        Path(video.video_file.name).suffix.lower()
        or ".mp4"
    )

    with tempfile.TemporaryDirectory() as temp_directory:
        temp_directory = Path(temp_directory)

        local_video_path = (
            temp_directory
            / f"source{video_extension}"
        )

        thumbnail_name = (
            f"video_{video.id}_thumbnail.jpg"
        )

        thumbnail_path = (
            temp_directory
            / thumbnail_name
        )

        try:
            video.video_file.open("rb")

            with local_video_path.open("wb") as local_file:
                while True:
                    chunk = video.video_file.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    local_file.write(chunk)

        except Exception as error:
            raise ThumbnailGenerationError(
                f"Could not download video: {error}"
            ) from error

        finally:
            video.video_file.close()

        capture = cv2.VideoCapture(
            str(local_video_path)
        )

        if not capture.isOpened():
            raise ThumbnailGenerationError(
                "OpenCV could not open the video."
            )

        try:
            frame_count = int(
                capture.get(
                    cv2.CAP_PROP_FRAME_COUNT
                )
                or 0
            )

            target_frame = (
                int(frame_count * 0.15)
                if frame_count > 0
                else 0
            )

            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                target_frame,
            )

            success, frame = capture.read()

            if not success:
                capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    0,
                )
                success, frame = capture.read()

            if not success:
                raise ThumbnailGenerationError(
                    "OpenCV could not read a video frame."
                )

            height, width = frame.shape[:2]
            maximum_width = 1280

            if width > maximum_width:
                scale = maximum_width / width

                frame = cv2.resize(
                    frame,
                    (
                        int(width * scale),
                        int(height * scale),
                    ),
                    interpolation=cv2.INTER_AREA,
                )

            saved = cv2.imwrite(
                str(thumbnail_path),
                frame,
                [
                    int(cv2.IMWRITE_JPEG_QUALITY),
                    88,
                ],
            )

            if not saved:
                raise ThumbnailGenerationError(
                    "OpenCV could not save the thumbnail."
                )

            with thumbnail_path.open("rb") as thumbnail_file:
                video.thumbnail.save(
                    thumbnail_name,
                    File(thumbnail_file),
                    save=False,
                )

            video.save(
                update_fields=["thumbnail"]
            )

        finally:
            capture.release()

    return video.thumbnail