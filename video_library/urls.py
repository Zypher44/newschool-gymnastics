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
        'analysis/<int:analysis_id>/review/',
        views.review_video_analysis,
        name='review_analysis',
    ),

    path(
        'analysis/moments/<int:moment_id>/review/',
        views.review_analysis_moment,
        name='review_analysis_moment',
    ),


    path(
        '<int:video_id>/analysis-history/',
        views.video_analysis_history,
        name='analysis_history',
    ),

    path(
        '<int:video_id>/analysis-rerun/',
        views.rerun_video_analysis,
        name='rerun_analysis',
    ),

    path(
        'analysis/<int:analysis_id>/',
        views.video_analysis_detail,
        name='analysis_detail',
    ),

    path(
        '<int:video_id>/',
        views.video_detail,
        name='video_detail',
    ),

    path(
        '<int:video_id>/analyze/',
        views.request_video_analysis,
        name='request_analysis',
    ),

    path(
        'analysis/<int:analysis_id>/status/',
        views.video_analysis_status,
        name='analysis_status',
    ),

    path(
        'analysis/<int:analysis_id>/process-mock/',
        views.process_mock_analysis,
        name='process_mock_analysis',
    ),

    path(
        '<int:video_id>/favorite/',
        views.toggle_video_favorite,
        name='toggle_favorite',
    ),
]