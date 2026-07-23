from django.urls import path

from . import views


urlpatterns = [
    path(
        '',
        views.report_center,
        name='report_center'
    ),

    path(
        'athlete-progress/',
        views.athlete_progress_report,
        name='athlete_progress_report'
    ),

    path(
        'team-readiness/',
        views.team_readiness_report,
        name='team_readiness_report'
    ),

    path(
        'attendance/',
        views.attendance_report,
        name='attendance_report'
    ),

    path(
        'wellness/',
        views.wellness_report,
        name='wellness_report'
    ),

    path(
        'testing/',
        views.testing_report,
        name='testing_report'
    ),

    path(
        'skills/',
        views.skill_report,
        name='skill_report'
    ),
]