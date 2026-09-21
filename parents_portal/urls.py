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


    path(
        'conditioning/',
        views.parent_conditioning_history,
        name='parent_conditioning_history',
    ),

    path(
        'conditioning/results/<int:result_id>/',
        views.parent_conditioning_result_detail,
        name='parent_conditioning_result_detail',
    ),
]
