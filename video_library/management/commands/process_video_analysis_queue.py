"""Continuous queue worker with subprocess deadlines and recoverable leases."""
import subprocess
import sys
import time
from django.core.management.base import BaseCommand
from video_library.analysis_queue import claim_analysis, finish_attempt, recover_expired_jobs


class Command(BaseCommand):
    help = 'Process queued video analyses. Run separately from the Django web server.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--poll-seconds', type=int, default=5)
        parser.add_argument('--timeout-seconds', type=int, default=600)

    def handle(self, *args, **options):
        timeout = max(1, options['timeout_seconds'])
        while True:
            recover_expired_jobs()
            job = claim_analysis(timeout_seconds=timeout)
            if job is None:
                if options['once']:
                    return
                time.sleep(max(1, options['poll_seconds']))
                continue
            error = None
            # Old database records may refer to media that was not copied to this
            # installation. Do not run native analysis or retry an absent source.
            source = job.video.video_file
            try:
                source_exists = bool(source and source.name and source.storage.exists(source.name))
            except Exception:
                # Network/permission errors do not establish that a file is absent.
                self.stderr.write(f'Storage check failed for video {job.video_id}; retaining normal retries.')
                finish_attempt(job.pk, job.worker_token, error='Source storage check failed')
                continue
            if not source_exists:
                self.stdout.write(f'Skipping video {job.video_id}: source file unavailable. No media or video records were deleted.')
                finish_attempt(job.pk, job.worker_token, source_missing=True)
                continue
            self.stdout.write(f'Analyzing video {job.video_id}, attempt {job.processing_attempts}.')
            try:
                # -m django preserves DJANGO_SETTINGS_MODULE set by manage.py or the local launcher.
                result = subprocess.run([
                    sys.executable, '-m', 'django', 'process_video_analysis',
                    '--analysis-id', str(job.pk), '--worker-token', str(job.worker_token),
                    '--timeout-seconds', str(timeout),
                ], timeout=timeout + 10, check=False)
                if result.returncode:
                    error = f'Processor exit code {result.returncode}'
            except subprocess.TimeoutExpired:
                error = 'Processing timed out'
            except OSError as exc:
                error = str(exc)
            finish_attempt(job.pk, job.worker_token, error=error)
