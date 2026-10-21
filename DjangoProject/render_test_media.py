"""Media is deliberately unavailable during core-only Render testing."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.storage import Storage
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin


class DisabledTestMediaStorage(Storage):
    def _open(self, name, mode='rb'):
        raise PermissionDenied('Video and media uploads are paused for this test.')

    def _save(self, name, content):
        raise PermissionDenied('Video and media uploads are paused for this test.')

    def exists(self, name):
        return False

    def url(self, name):
        return ''


class TestMediaMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(settings, 'RENDER_TEST_VIDEOS_ENABLED', False):
            return None
        if not getattr(request.user, 'is_authenticated', False):
            return None
        match = request.resolver_match
        video_page = match and (
            'video_library' in match.namespaces or match.url_name in {
                'upload_athlete_video', 'update_video_review',
                'parent_video_library', 'parent_video_detail',
            })
        media_upload = request.method in {'POST', 'PUT', 'PATCH'} and bool(request.FILES)
        if video_page or media_upload:
            return render(request, 'render_test_videos_paused.html',
                          status=200 if request.method in {'GET', 'HEAD'} else 409)
        return None
