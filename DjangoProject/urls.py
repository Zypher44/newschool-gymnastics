from django.contrib import admin
from django.urls import include, path
from accounts import public_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path(
        '',
        public_views.home,
        name='home',
    ),


    path('admin/', admin.site.urls),

    path(
        'accounts/',
        include('accounts.urls')
    ),

    path(
        'coaches/',
        include('coaches.urls')
    ),

    path(
        'athletes/',
        include('athletes.urls')
    ),

    path(
        'parents/',
        include('parents_portal.urls')
    ),

    path(
        'surveys/',
        include('surveys.urls')
    ),

    path(
        'testing/',
        include('performance_testing.urls')
    ),

    path(
        'communications/',
        include('communications.urls')
    ),
    path(
        'reports/',
        include('reports.urls')
    ),

    path(
        'practice-planner/',
        include('practice_planner.urls'),
    ),

    path(
        'videos/',
        include('video_library.urls'),
    ),

    path(
        'pathway/',
        include(
        'pathway.urls'
        ),
    ),

    path(
        'routine-tracker/',
        include(
        'routine_tracker.urls'
        ),
    ),

    path(
        'gyms/',
        include('gyms.urls')
    ),


]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

handler403 = 'accounts.error_views.custom_403'
handler404 = 'accounts.error_views.custom_404'
handler500 = 'accounts.error_views.custom_500'