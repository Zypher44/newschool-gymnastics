from django.urls import path

from . import views


urlpatterns = [

    path(
        'director/',
        views.director_dashboard,
        name='director_dashboard'
    ),

    path(
        'groups/create/',
        views.create_training_group,
        name='create_training_group'
    ),

    path(
        'groups/<int:group_id>/',
        views.group_control_panel,
        name='group_control_panel'
    ),

    path(
        'groups/<int:group_id>/edit/',
        views.edit_training_group,
        name='edit_training_group'
    ),

    path(
        'groups/<int:group_id>/coaches/',
        views.manage_group_coaches,
        name='manage_group_coaches'
    ),

    path(
        'groups/<int:group_id>/athletes/',
        views.manage_group_athletes,
        name='manage_group_athletes'
    ),

path(
    'people/',
    views.people_management,
    name='people_management'
),

    path(
        'people/add/',
        views.create_gym_person,
        name='create_gym_person'
    ),

    path(
        'people/<int:membership_id>/edit/',
        views.edit_gym_person,
        name='edit_gym_person'
    ),

    path(
        'people/<int:membership_id>/status/',
        views.toggle_gym_person_status,
        name='toggle_gym_person_status'
    ),

    path(
        'athletes/<int:athlete_id>/',
        views.director_athlete_profile,
        name='director_athlete_profile'
    ),


    path(
        'athletes/<int:athlete_id>/link-parent/',
        views.link_parent_guardian,
        name='link_parent_guardian',
    ),

    path(
        'events/',
        views.director_event_list,
        name='director_event_list'
    ),

    path(
        'events/<int:event_id>/edit/',
        views.edit_gym_event,
        name='edit_gym_event'
    ),

    path(
        'events/<int:event_id>/delete/',
        views.delete_gym_event,
        name='delete_gym_event'
    ),


    path(
        'parent-links/<int:link_id>/approve/',
        views.approve_parent_link,
        name='approve_parent_link',
    ),

    path(
        'parent-links/<int:link_id>/decline/',
        views.decline_parent_link,
        name='decline_parent_link',
    ),

]