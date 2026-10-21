from django.urls import path

from . import views
from . import roster_views
from .roster_invitations import RosterPasswordSetup
from .usage_views import gym_usage
from .login_help import reset_person_password, calendar_instead_of_events
from gym_scheduling.views import schedules, session_exceptions


urlpatterns = [
    path('people/roster/', roster_views.roster_import, name='roster_import'),
    path('people/roster/download/', roster_views.roster_download, name='roster_download'),
    path('people/roster/<uuid:batch_id>/', roster_views.roster_preview, name='roster_import_preview'),
    path('account-setup/<uidb64>/<token>/', RosterPasswordSetup.as_view(), name='roster_password_setup'),
    path('people/<int:membership_id>/reset-password/', reset_person_password,
         name='reset_gym_person_password'),
    path('schedules/<int:schedule_id>/exceptions/', session_exceptions, name='group_schedule_exceptions'),
    path('schedules/', schedules, name='group_schedules'),
    path('schedules/<int:schedule_id>/edit/', schedules, name='group_schedule_edit'),
    path('usage/', gym_usage, name='gym_usage'),

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
    path('people/<int:membership_id>/coach-role/', views.set_coach_role,
         name='set_coach_role'),

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
        calendar_instead_of_events,
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

    path('settings/', views.gym_settings, name='gym_settings'),

]

