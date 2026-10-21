"""Bounded local copies for local and remote Django storage backends."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
from django.conf import settings


@contextmanager
def local_storage_file(field_file, *, maximum_bytes=None):
    if not field_file or not field_file.name:
        raise ValueError('The source file is missing.')
    limit = maximum_bytes or getattr(settings, 'VIDEO_MAX_SOURCE_BYTES', 500 * 1024 * 1024)
    suffix = Path(field_file.name).suffix[:16] or '.bin'
    with tempfile.TemporaryDirectory(prefix='gym-video-') as directory:
        destination = Path(directory) / ('source' + suffix)
        count = 0
        with field_file.storage.open(field_file.name, 'rb') as source:
            with destination.open('wb') as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > limit:
                        raise ValueError('The source exceeds the video processing size limit.')
                    target.write(chunk)
        if not count:
            raise ValueError('The source file is empty.')
        yield destination
