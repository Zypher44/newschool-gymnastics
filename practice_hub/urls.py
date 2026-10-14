from django.urls import path
from . import views, onboarding

app_name = 'practice_hub'
urlpatterns = [
    path('start/', views.start_practice, name='start'),
    path('getting-started/', onboarding.getting_started, name='onboarding'),
]
