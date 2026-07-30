from django.urls import path

from . import views


app_name = 'practice_planner'


urlpatterns = [
    path(
        '',
        views.practice_dashboard,
        name='dashboard',
    ),

    path(
        'groups/',
        views.training_group_list,
        name='training_group_list',
    ),

    path(
        'groups/create/',
        views.training_group_create,
        name='training_group_create',
    ),

    path(
        'groups/<int:group_id>/',
        views.training_group_detail,
        name='training_group_detail',
    ),

    path(
        'groups/<int:group_id>/edit/',
        views.training_group_update,
        name='training_group_update',
    ),

    path(
        'practices/create/',
        views.practice_create,
        name='practice_create',
    ),

    path(
        'practices/<int:practice_id>/',
        views.practice_detail,
        name='practice_detail',
    ),

    path(
        'practices/<int:practice_id>/edit/',
        views.practice_update,
        name='practice_update',
    ),

    path(
        'practices/<int:practice_id>/builder/',
        views.practice_builder,
        name='practice_builder',
    ),

    path(
        'practices/<int:practice_id>/start/',
        views.practice_start,
        name='practice_start',
    ),

    path(
        'practices/<int:practice_id>/complete/',
        views.practice_complete,
        name='practice_complete',
    ),

    path(
        'practices/<int:practice_id>/testing/create/',
        views.create_testing_session_for_practice,
        name='create_testing_session_for_practice',
    ),

    path(
        'practices/<int:practice_id>/rotations/create/',
        views.rotation_create,
        name='rotation_create',
    ),

    path(
        'practices/<int:practice_id>/save-template/',
        views.save_practice_as_template,
        name='save_practice_as_template',
    ),

    path(
        'templates/',
        views.practice_template_list,
        name='practice_template_list',
    ),

    path(
        'templates/<int:template_id>/',
        views.practice_template_detail,
        name='practice_template_detail',
    ),

    path(
        'rotations/<int:rotation_id>/edit/',
        views.rotation_update,
        name='rotation_update',
    ),

    path(
        'practices/<int:practice_id>/rotations/reorder/',
        views.reorder_rotations,
        name='reorder_rotations',
    ),

    path(
        'rotations/<int:rotation_id>/stations/reorder/',
        views.reorder_stations,
        name='reorder_stations',
    ),

    path(
        'rotations/<int:rotation_id>/delete/',
        views.rotation_delete,
        name='rotation_delete',
    ),

    path(
        'rotations/<int:rotation_id>/stations/create/',
        views.station_create,
        name='station_create',
    ),

    path(
        'stations/<int:station_id>/edit/',
        views.station_update,
        name='station_update',
    ),

    path(
        'stations/<int:station_id>/delete/',
        views.station_delete,
        name='station_delete',
    ),

    path(
        'assignments/<int:assignment_id>/edit/',
        views.athlete_assignment_update,
        name='athlete_assignment_update',
    ),

    path(
        'templates/<int:template_id>/create-practice/',
        views.create_practice_from_template,
        name='create_practice_from_template',
    ),


]