from django.urls import path

from . import views


app_name = 'video_library'


urlpatterns = [
    path(
        '',
        views.video_dashboard,
        name='dashboard',
    ),

    path(
        'library/',
        views.video_list,
        name='video_list',
    ),

    path(
        'upload/',
        views.video_upload,
        name='upload',
    ),

    path(
        'athletes/<int:athlete_id>/',
        views.athlete_video_timeline,
        name='athlete_timeline',
    ),

    path(
        'athletes/<int:athlete_id>/compare/',
        views.athlete_video_compare_select,
        name='compare_select',
    ),

    path(
        'compare/',
        views.video_compare,
        name='video_compare',
    ),

    path(
        '<int:video_id>/',
        views.video_detail,
        name='video_detail',
    ),

    path(
        '<int:video_id>/favorite/',
        views.toggle_video_favorite,
        name='toggle_favorite',
    ),
]