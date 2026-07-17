from django.urls import path

from . import views


urlpatterns = [
    path(
        '',
        views.testing_session_list,
        name='testing_session_list'
    ),

    path(
        'sessions/create/',
        views.create_testing_session,
        name='create_testing_session'
    ),

    path(
        'sessions/<int:session_id>/',
        views.testing_session_detail,
        name='testing_session_detail'
    ),

    path(
        'exercises/',
        views.testing_exercise_list,
        name='testing_exercise_list'
    ),

    path(
        'exercises/create/',
        views.create_testing_exercise,
        name='create_testing_exercise'
    ),

    path(
        'exercises/<int:exercise_id>/edit/',
        views.edit_testing_exercise,
        name='edit_testing_exercise'
    ),

    path(
        'exercises/<int:exercise_id>/toggle/',
        views.toggle_testing_exercise,
        name='toggle_testing_exercise'
    ),
    path(
        'sessions/<int:session_id>/publish/',
        views.publish_testing_session,
        name='publish_testing_session'
    ),

    path(
        'athlete/history/',
        views.athlete_testing_history,
        name='athlete_testing_history'
    ),

    path(
        'athlete/results/<int:result_id>/',
        views.athlete_testing_result_detail,
        name='athlete_testing_result_detail'
    ),
]