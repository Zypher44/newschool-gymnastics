import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

from django.core.files import File


class VideoConversionError(Exception):
    pass


def _download_video(video, destination):
    try:
        video.video_file.open('rb')

        with destination.open('wb') as local_file:
            for chunk in iter(
                lambda: video.video_file.read(1024 * 1024),
                b'',
            ):
                local_file.write(chunk)

    except Exception as error:
        raise VideoConversionError(
            f'Could not download the source video: {error}'
        ) from error

    finally:
        try:
            video.video_file.close()
        except Exception:
            pass


def convert_video_to_mp4(video):
    """
    Convert a Django FileField video to a browser-compatible MP4.

    Works with both local storage and S3-compatible Supabase storage.
    The source object is deleted only after the converted file has been
    uploaded and saved successfully.
    """

    if not video.video_file:
        raise VideoConversionError('Video file is missing.')

    original_storage = video.video_file.storage
    original_name = video.video_file.name
    original_extension = (
        Path(original_name).suffix.lower()
        or '.video'
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_directory = Path(temporary_directory)
        source_path = temporary_directory / f'source{original_extension}'
        output_path = temporary_directory / 'converted.mp4'

        _download_video(video, source_path)

        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            '-hide_banner',
            '-loglevel',
            'error',
            '-y',
            '-i',
            str(source_path),
            '-map',
            '0:v:0',
            '-map',
            '0:a?',
            '-c:v',
            'libx264',
            '-preset',
            'veryfast',
            '-crf',
            '23',
            '-pix_fmt',
            'yuv420p',
            '-vf',
            'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-c:a',
            'aac',
            '-b:a',
            '128k',
            '-movflags',
            '+faststart',
            '-sn',
            str(output_path),
        ]

        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if completed_process.returncode != 0:
            error_message = (
                completed_process.stderr.strip()
                or 'FFmpeg returned an unknown error.'
            )
            raise VideoConversionError(error_message[-2000:])

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoConversionError(
                'FFmpeg did not create a usable MP4 file.'
            )

        converted_filename = (
            f'{Path(video.original_filename or original_name).stem}.mp4'
        )

        with output_path.open('rb') as converted_file:
            video.video_file.save(
                converted_filename,
                File(converted_file),
                save=False,
            )

        video.content_type = 'video/mp4'
        video.file_size_bytes = output_path.stat().st_size
        video.processing_error = ''
        video.save(
            update_fields=[
                'video_file',
                'content_type',
                'file_size_bytes',
                'processing_error',
                'updated_at',
            ],
        )

    if original_name != video.video_file.name:
        try:
            original_storage.delete(original_name)
        except Exception:
            # The converted file is already safe. A failed cleanup should
            # not make an otherwise successful conversion unavailable.
            pass

    return video
