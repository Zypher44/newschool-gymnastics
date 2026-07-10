
from django.urls import path
from .views import submit_survey, survey_success

urlpatterns = [
    path('submit/', submit_survey, name='submit_survey'),
    path('success/', survey_success, name='survey_success'),
    ]
