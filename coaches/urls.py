from django.urls import path

from .views import (
    coach_dashboard,
    athlete_detail,
    add_event,
    take_attendance,
    update_athlete_skill,
    upload_athlete_video,
    athlete_skill_detail,
    update_video_review,
)
urlpatterns = [
    path('dashboard/', coach_dashboard, name='coach_dashboard'),

    path('athlete/<int:athlete_id>/', athlete_detail, name='athlete_detail'),

    path(
        'athlete/<int:athlete_id>/skills/<int:athlete_skill_id>/',
        athlete_skill_detail,
        name='athlete_skill_detail'
    ),

    path(
        'athlete/<int:athlete_id>/skills/<int:athlete_skill_id>/update/',
        update_athlete_skill,
        name='update_athlete_skill'
    ),

    path(
        'athlete/<int:athlete_id>/videos/upload/',
        upload_athlete_video,
        name='upload_athlete_video'
    ),
    path(
        'athlete/<int:athlete_id>/videos/<int:video_id>/review/',
        update_video_review,
        name='update_video_review'
    ),

    path('events/add/', add_event, name='add_event'),
    path('attendance/', take_attendance, name='take_attendance'),
]