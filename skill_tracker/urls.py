from django.urls import path
from . import views
app_name = 'skill_tracker'
urlpatterns = [
    path('', views.tracker, name='tracker'),
    path('manage/', views.manage, name='manage'),
    path('save/', views.save_results, name='save'),
]
