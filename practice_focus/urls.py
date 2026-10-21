from django.urls import path
from . import views

app_name = 'practice_focus'
urlpatterns = [path('', views.planner, name='planner')]


# V3 individual practice plans
from . import personal_views as individual_views
from django.urls import path as individual_path
urlpatterns = [
    individual_path('', individual_views.planner, name='planner'),
    individual_path('my-plan/', individual_views.my_plan, name='my_plan'),
    *[entry for entry in urlpatterns if getattr(entry, 'name', None) not in ('planner', 'my_plan')],
]

# V3 coach report preferences
from .report_preferences import save_report_settings
urlpatterns += [path('report-settings/', save_report_settings, name='report_settings')]

# V3 practice progress upgrades

from . import engagement_views, tracking_api
urlpatterns += [
    path('tracking/state/', tracking_api.tracker_state, name='tracker_state'),
    path('tracking/save/', tracking_api.tracker_mutate, name='tracker_mutate'),
    path('review-queue/', engagement_views.review_queue, name='review_queue'),
    path('feedback/', engagement_views.coach_feedback, name='coach_feedback'),
    path('weekly-reports/', engagement_views.weekly_reports, name='weekly_reports'),
    path('weekly-reports/<int:summary_id>/', engagement_views.weekly_report_detail, name='weekly_report_detail'),
    path('my-progress/', engagement_views.family_progress, name='family_progress'),
]

# V3 report email delivery

from . import email_views
urlpatterns += [
    path('email-reports/preview/<slug:kind>/', email_views.email_report_preview, name='email_report_preview'),
    path('email-reports/<int:draft_id>/', email_views.email_report_detail, name='email_report_detail'),
]

# V3 Practice Passport
from django.urls import path as passport_path
from . import passport_views as passport_pages
urlpatterns += [
    passport_path('practice-passports/', passport_pages.coach_passport, name='coach_passport'),
    passport_path('my-passport/', passport_pages.family_passport, name='family_passport'),
]

# V3 coach badge library
from django.urls import path as badge_library_path
from .passport_badge_views import badge_editor as coach_badge_editor
urlpatterns += [badge_library_path('practice-passports/badges/', coach_badge_editor, name='badge_editor')]

# V3 badge deletion
from django.urls import path as delete_badge_path
from .passport_badge_views import badge_delete as delete_passport_badge
urlpatterns += [delete_badge_path('practice-passports/badges/<slug:code>/<slug:variant>/delete/', delete_passport_badge, name='badge_delete')]

# V3 dated athlete practice journal
from . import journal_views
urlpatterns += [
    path('journal/', journal_views.journal_history, name='journal_history'),
    path('journal/new/', journal_views.journal_edit, name='journal_new'),
    path('journal/<int:entry_id>/', journal_views.journal_detail, name='journal_detail'),
    path('journal/<int:entry_id>/edit/', journal_views.journal_edit, name='journal_edit'),
]
