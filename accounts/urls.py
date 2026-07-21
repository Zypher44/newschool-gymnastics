from django.contrib.auth import views as auth_views
from django.urls import path

from .redirect_views import role_redirect


urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

    path(
        'redirect/',
        role_redirect,
        name='role_redirect'
    ),
]