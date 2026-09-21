from django.urls import path

from . import views


urlpatterns = [
    path(
        'dashboard/',
        views.parent_dashboard,
        name='parent_dashboard',
    ),

    path(
        'connect-athlete/',
        views.connect_athlete,
        name='connect_athlete',
    ),

    path(
        'events/',
        views.parent_events,
        name='parent_events',
    ),

    path(
        'videos/',
        views.parent_video_library,
        name='parent_video_library',
    ),

    path(
        'videos/<int:video_id>/',
        views.parent_video_detail,
        name='parent_video_detail',
    ),
]