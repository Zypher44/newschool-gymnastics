from django.urls import path

from . import views


urlpatterns = [
    path(
        'dashboard/',
        views.parent_dashboard,
        name='parent_dashboard'
    ),

    path(
        'connect-athlete/',
        views.connect_athlete,
        name='connect_athlete'
    ),
]