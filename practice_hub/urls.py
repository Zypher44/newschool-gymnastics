from django.urls import path
from . import views, onboarding

app_name = 'practice_hub'
urlpatterns = [
    path('getting-started/dismiss/', onboarding.dismiss_guide, name='dismiss_guide'),
    path('start/', views.start_practice, name='start'),
    path('getting-started/', onboarding.getting_started, name='onboarding'),
]
