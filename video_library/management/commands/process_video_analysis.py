"""One leased analysis, normally started by the queue worker."""
import signal
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from video_library.models import VideoAnalysis


class Command(BaseCommand):
    help = 'Process one analysis claimed by process_video_analysis_queue.'

    def add_arguments(self, parser):
        parser.add_argument('--analysis-id', type=int, required=True)
        parser.add_argument('--worker-token', required=True)
        parser.add_argument('--timeout-seconds', type=int, default=600)

    def handle(self, *args, **options):
        analysis = VideoAnalysis.objects.select_related('video').filter(
            pk=options['analysis_id'], worker_token=options['worker_token'],
            lease_expires_at__gt=timezone.now(), status=VideoAnalysis.STATUS_PREPARING,
        ).first()
        if analysis is None:
            raise CommandError('This job is no longer leased to this worker.')
        previous = None
        if hasattr(signal, 'SIGALRM'):
            # SIG_DFL terminates even a blocked native C/C++ call.
            previous = signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.alarm(max(1, options['timeout_seconds']))
        try:
            from video_library.ai.processor import VideoAnalysisProcessor
            VideoAnalysisProcessor().process(analysis)
        finally:
            if previous is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous)
