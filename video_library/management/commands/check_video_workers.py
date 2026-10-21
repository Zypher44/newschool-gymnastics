from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Check the installed FFmpeg binary and MediaPipe model/native libraries.'

    def handle(self, *args, **options):
        import subprocess
        try:
            import imageio_ffmpeg
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-version'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            from video_library.ai.pose import MediaPipePoseEngine
            engine = MediaPipePoseEngine()
            engine.close()
        except Exception as error:
            raise CommandError('Video worker is not ready. Verify FFmpeg, the pose model and MediaPipe Linux native dependencies. Details: ' + str(error)) from error
        self.stdout.write(self.style.SUCCESS('FFmpeg and the MediaPipe pose model are ready.'))
