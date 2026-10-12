from django.db import connection
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from .urls import urlpatterns, handler403, handler404, handler500


@never_cache
@require_safe
def test_health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'not_ready', 'environment': 'test'}, status=503)
    return JsonResponse({'status': 'ok', 'environment': 'test'})


class TestResponseHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        response['X-Newschool-Environment'] = 'test'
        return response


urlpatterns = [path('_render-test/health/', test_health, name='render_test_health'), *urlpatterns]
