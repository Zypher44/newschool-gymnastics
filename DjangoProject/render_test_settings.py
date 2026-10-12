"""Separate settings used only by the proposed Render test services."""
from django.core.exceptions import ImproperlyConfigured
from .settings import *

RENDER_TEST_ENVIRONMENT = True

if DEBUG:
    raise ImproperlyConfigured('The public test service requires DJANGO_DEBUG=False.')
if not DATABASE_URL:
    raise ImproperlyConfigured('The test service requires its own PostgreSQL DATABASE_URL.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('A separate PostgreSQL test database is required.')
if DATABASES['default']['NAME'] != 'newschool_v2_test':
    raise ImproperlyConfigured('Refusing the database: use the separate newschool_v2_test database.')
if not USE_SUPABASE_STORAGE or SUPABASE_STORAGE_BUCKET != 'athlete-videos-test':
    raise ImproperlyConfigured('Use a private athlete-videos-test storage bucket for the test environment.')

STORAGES['default']['OPTIONS']['location'] = 'render-test'
ROOT_URLCONF = 'DjangoProject.render_test_urls'
MIDDLEWARE = [*MIDDLEWARE, 'DjangoProject.render_test_urls.TestResponseHeaders']

# Report delivery uses a provider directly, independently of Django EMAIL_BACKEND.
# Keep it unconfigured until an explicit test delivery setup is requested.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
REPORT_EMAIL_API_KEY = ''
REPORT_EMAIL_FROM = ''
REPORT_EMAIL_APP_URL = ''
SESSION_COOKIE_NAME = 'newschool_render_test_session'
CSRF_COOKIE_NAME = 'newschool_render_test_csrf'
