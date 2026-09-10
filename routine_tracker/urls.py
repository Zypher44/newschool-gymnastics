from django.urls import path

from . import views


app_name = 'routine_tracker'


urlpatterns = [

    path(
        '',
        views.daily_routine_tracker,
        name='daily_routine_tracker',
    ),

    path(
        'attempt/add/',
        views.add_routine_attempt,
        name='add_routine_attempt',
    ),

    path(
        'attempt/<int:attempt_id>/delete/',
        views.delete_routine_attempt,
        name='delete_routine_attempt',
    ),

    path(
        'summary/',
        views.routine_consistency_summary,
        name='routine_consistency_summary',
    ),

    path(
        'my-consistency/',
        views.athlete_routine_consistency,
        name='athlete_routine_consistency',
    ),

    path(
        'parent/consistency/',
        views.parent_routine_consistency_home,
        name='parent_routine_consistency_home',
    ),

    path(
        'parent/consistency/<int:athlete_id>/',
        views.parent_routine_consistency,
        name='parent_routine_consistency',
    ),
]