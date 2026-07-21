from django.urls import path

from . import views


urlpatterns = [
    path(
        'dashboard/',
        views.athlete_dashboard,
        name='athlete_dashboard'
    ),
]