from django.contrib import admin
from django.urls import include, path
from accounts import public_views
from accounts import enquiry_views
from communications.safety_views import safety_support
from accounts.info_views import public_info
from accounts import signup_v2
from coaches.calendar_views import gym_calendar
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('safety/', safety_support, name='safety_support'),
    path('demo/', enquiry_views.enquiry, name='public_demo'),
    path('enquiry/received/', enquiry_views.received, name='public_enquiry_received'),
    path('product/enquiries/', enquiry_views.inbox, name='public_enquiry_inbox'),
    path('features/', public_info, {'slug': 'features'}, name='public_features'),
    path('pricing/', public_info, {'slug': 'pricing'}, name='public_pricing'),
    path('roadmap/', public_info, {'slug': 'roadmap'}, name='public_roadmap'),
    path('help/', public_info, {'slug': 'help'}, name='public_help'),
    path('contact/', enquiry_views.enquiry, {'kind': 'support'}, name='public_contact'),
    path('support/', public_info, {'slug': 'support'}, name='public_support'),
    path('privacy/', public_info, {'slug': 'privacy'}, name='public_privacy'),
    path('terms/', public_info, {'slug': 'terms'}, name='public_terms'),
    path('cookies/', public_info, {'slug': 'cookies'}, name='public_cookies'),

    path('calendar/', gym_calendar, name='gym_calendar'),
    path('accounts/signup/director/', signup_v2.director_signup, name='director_signup'),
    path('accounts/signup/', signup_v2.member_signup, name='signup'),
    path(
        '',
        public_views.home,
        name='home',
    ),


    path('admin/', admin.site.urls),

    path(
        'accounts/',
        include('accounts.urls')
    ),

    path(
        'coaches/',
        include('coaches.urls')
    ),

    path(
        'athletes/',
        include('athletes.urls')
    ),

    path(
        'parents/',
        include('parents_portal.urls')
    ),

    path(
        'surveys/',
        include('surveys.urls')
    ),

    path(
        'testing/',
        include('performance_testing.urls')
    ),

    path(
        'communications/',
        include('communications.urls')
    ),
    path(
        'reports/',
        include('reports.urls')
    ),

    path(
        'practice-planner/',
        include('practice_planner.urls'),
    ),

    path(
        'videos/',
        include('video_library.urls'),
    ),

    path(
        'pathway/',
        include(
        'pathway.urls'
        ),
    ),

    path(
        'routine-tracker/',
        include(
        'routine_tracker.urls'
        ),
    ),

    path(
        'gyms/',
        include('gyms.urls')
    ),


]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

handler403 = 'accounts.error_views.custom_403'
handler404 = 'accounts.error_views.custom_404'
handler500 = 'accounts.error_views.custom_500'


# V3 current-skills workspace
from django.urls import include as focus_include, path as focus_path
urlpatterns.insert(0, focus_path('practice-planner/current-skills/', focus_include('practice_focus.urls')))


# V3 Skill Tracker
from django.urls import include as skills_include, path as skills_path
urlpatterns.insert(0, skills_path('skill-tracker/', skills_include('skill_tracker.urls')))


# V3 Start Practice and guided onboarding
from django.urls import include as hub_include, path as hub_path
urlpatterns.insert(0, hub_path('practice/', hub_include('practice_hub.urls')))
