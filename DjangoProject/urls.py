from django.contrib import admin
from django.urls import include, path


urlpatterns = [
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
]