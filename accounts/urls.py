from django.contrib.auth import views as auth_views
from django.urls import path

from . import public_views
from . import redirect_views
from . import views

from .redirect_views import role_redirect
from .recovery import AccountRecoveryView


urlpatterns = [
    path('password-reset/', AccountRecoveryView.as_view(), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/account_recovery_done.html'), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/account_recovery_confirm.html'), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/account_recovery_complete.html'), name='password_reset_complete'),
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

    path(
        'signup/',
        public_views.signup,
        name='signup',
    ),

    path(
        'settings/',
        views.account_settings,
        name='account_settings',
    ),

    path(
        'redirect/',
        redirect_views.role_redirect,
        name='role_redirect',
    ),

]
