"""Run conversion and analysis consumers from one local/Render command."""
import os
import signal
import subprocess
import sys
import time
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run both video queues. Keep this running alongside the web server.'

    def handle(self, *args, **options):
        call_command('check_video_workers')
        children = []
        def stop(*_):
            raise KeyboardInterrupt
        previous = signal.signal(signal.SIGTERM, stop)
        try:
            for command in ('process_video_queue', 'process_video_analysis_queue'):
                children.append(subprocess.Popen([sys.executable, '-m', 'django', command],
                                                  start_new_session=(os.name == 'posix')))
            self.stdout.write('Video conversion and analysis workers started. Ctrl+C stops both.')
            while True:
                if any(child.poll() is not None for child in children):
                    raise CommandError('A video worker stopped. Check its output and restart process_video_jobs.')
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write('Stopping video workers.')
        finally:
            signal.signal(signal.SIGTERM, previous)
            for child in children:
                if child.poll() is None:
                    if os.name == 'posix':
                        try:
                            os.killpg(child.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    else:
                        child.terminate()
            for child in children:
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        child.kill()
                    child.wait()
