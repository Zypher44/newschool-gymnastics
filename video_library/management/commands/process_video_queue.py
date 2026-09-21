import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from video_library.ai.conversion_service import convert_video_to_mp4
from video_library.ai.video_service import process_video_file
from video_library.models import Video


class Command(BaseCommand):
    help = 'Convert queued videos to browser-compatible MP4 files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Process the current queue and then exit.',
        )
        parser.add_argument(
            '--poll-seconds',
            type=int,
            default=5,
            help='Seconds to wait when the queue is empty.',
        )

    def handle(self, *args, **options):
        once = options['once']
        poll_seconds = max(options['poll_seconds'], 1)

        stale_before = timezone.now() - timedelta(hours=1)
        recovered = Video.objects.filter(
            status=Video.STATUS_PROCESSING,
            updated_at__lt=stale_before,
        ).update(
            status=Video.STATUS_UPLOADING,
            processing_error='',
        )

        if recovered:
            self.stdout.write(
                f'Recovered {recovered} interrupted conversion(s).'
            )

        while True:
            video = self._claim_next_video()

            if video is None:
                if once:
                    return

                time.sleep(poll_seconds)
                continue

            self._process_video(video)

    @staticmethod
    def _claim_next_video():
        with transaction.atomic():
            video = (
                Video.objects
                .select_for_update(skip_locked=True)
                .filter(status=Video.STATUS_UPLOADING)
                .order_by('created_at')
                .first()
            )

            if video is None:
                return None

            video.status = Video.STATUS_PROCESSING
            video.processing_error = ''
            video.save(
                update_fields=[
                    'status',
                    'processing_error',
                    'updated_at',
                ],
            )

            return video

    def _process_video(self, video):
        self.stdout.write(f'Converting video {video.id}: {video.title}')

        try:
            convert_video_to_mp4(video)
            process_video_file(video)

            video.status = Video.STATUS_READY
            video.processing_error = ''
            video.save(
                update_fields=[
                    'status',
                    'processing_error',
                    'updated_at',
                ],
            )

        except Exception as error:
            video.status = Video.STATUS_FAILED
            video.processing_error = str(error)[:4000]
            video.save(
                update_fields=[
                    'status',
                    'processing_error',
                    'updated_at',
                ],
            )

            self.stderr.write(
                self.style.ERROR(
                    f'Video {video.id} failed: {error}'
                )
            )

        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Video {video.id} is ready.'
                )
            )
