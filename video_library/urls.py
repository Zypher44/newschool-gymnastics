from django.urls import path

from . import views, skill_library_views, progress_views, moment_feedback_views


app_name = 'video_library'


urlpatterns = [
    path('<int:video_id>/feedback/', moment_feedback_views.feedback_page, name='moment_feedback'),
    path('<int:video_id>/moments/', moment_feedback_views.moments, name='video_moments'),
    path('<int:video_id>/moments/<int:note_id>/', moment_feedback_views.change_moment, name='change_video_moment'),
    path('progress/', progress_views.index, name='video_progress'),
    path('skill-library/', skill_library_views.library, name='skill_library'),
    path('skill-library/upload/', skill_library_views.upload, name='skill_example_upload'),
    path('skill-library/<int:video_id>/', skill_library_views.detail, name='skill_example_detail'),
    path('skill-library/<int:video_id>/edit/', skill_library_views.edit, name='skill_example_edit'),
    path('skill-library/<int:video_id>/add/', skill_library_views.add_existing, name='add_skill_example'),
    path('skill-library/<int:video_id>/approve/', skill_library_views.approval, name='approve_skill_example'),
    path('skill-library/<int:video_id>/remove/', skill_library_views.remove, name='remove_skill_example'),
    path(
        '',
        views.video_dashboard,
        name='dashboard',
    ),

    path(
        'my-videos/',
        views.family_video_library,
        name='family_library',
    ),

    path(
        'library/',
        views.video_list,
        name='video_list',
    ),

    path(
        'mock-meets/',
        views.mock_meet_library,
        name='mock_meets',
    ),

    path(
        'upload/',
        views.video_upload,
        name='upload',
    ),

    path(
        'athletes/<int:athlete_id>/',
        progress_views.timeline,
        name='athlete_timeline',
    ),

    path(
        'athletes/<int:athlete_id>/compare/',
        views.athlete_video_compare_select,
        name='compare_select',
    ),

    path(
        'compare/',
        views.video_compare,
        name='video_compare',
    ),

    path(
        'analysis/<int:analysis_id>/review/',
        views.review_video_analysis,
        name='review_analysis',
    ),

    path(
        'analysis/moments/<int:moment_id>/review/',
        views.review_analysis_moment,
        name='review_analysis_moment',
    ),


    path(
        '<int:video_id>/analysis-history/',
        views.video_analysis_history,
        name='analysis_history',
    ),

    path(
        '<int:video_id>/analysis-rerun/',
        views.rerun_video_analysis,
        name='rerun_analysis',
    ),

    path(
        'analysis/<int:analysis_id>/',
        views.video_analysis_detail,
        name='analysis_detail',
    ),

    path(
        '<int:video_id>/process-video/',
        views.process_video_metadata,
        name='process_video_metadata',
    ),

    path(
        '<int:video_id>/extract-frames/',
        views.extract_video_analysis_frames,
        name='extract_analysis_frames',
    ),

    path(
        '<int:video_id>/detect-pose/',
        views.detect_video_pose,
        name='detect_video_pose',
    ),

    path(
        '<int:video_id>/generate-pose-overlays/',
        views.generate_pose_overlays,
        name='generate_pose_overlays',
    ),

    path(
        'analysis/<int:first_analysis_id>/compare/',
        views.start_analysis_comparison,
        name='start_analysis_comparison',
    ),


    path(
        'analysis/compare/<int:first_analysis_id>/<int:second_analysis_id>/',
        views.compare_video_analyses,
        name='compare_analyses',
    ),



    path(
        '<int:video_id>/',
        views.video_detail,
        name='video_detail',
    ),

    path(
        'athlete/<int:athlete_id>/compare/',
        views.athlete_video_compare_select,
        name='athlete_video_compare_select',
    ),

    path(
        '<int:video_id>/analyze/',
        views.request_video_analysis,
        name='request_analysis',
    ),

    path(
        'analysis/<int:analysis_id>/status/',
        views.video_analysis_status,
        name='analysis_status',
    ),

    path(
        'analysis/<int:analysis_id>/process-mock/',
        views.process_mock_analysis,
        name='process_mock_analysis',
    ),

    path(
        '<int:video_id>/favorite/',
        views.toggle_video_favorite,
        name='toggle_favorite',
    ),

    path(
        'technique-profiles/',
        views.technique_profile_list,
        name='technique_profile_list',
    ),

    path(
        'technique-profiles/new/',
        views.technique_profile_create,
        name='technique_profile_create',
    ),

    path(
        'technique-profiles/<int:profile_id>/edit/',
        views.technique_profile_edit,
        name='technique_profile_edit',
    ),

    path(
        'athlete/<int:athlete_id>/progress/',
        views.athlete_skill_progress,
        name='athlete_skill_progress',
    ),

    path(
        'athlete/<int:athlete_id>/timeline/',
        progress_views.timeline,
        name='athlete_video_timeline',
    ),
    path(
        'video/<int:video_id>/personal-best/',
        views.toggle_personal_best,
        name='toggle_personal_best',
    ),


    path(
        'video/<int:video_id>/reference-attempt/',
        views.toggle_reference_attempt,
        name='toggle_reference_attempt',
    ),

    path(
        'video/<int:video_id>/coaching-example/',
        views.toggle_coaching_example,
        name='toggle_coaching_example',
    ),

    path(
        'athlete/<int:athlete_id>/skill-goal/create/',
        views.create_skill_goal,
        name='create_skill_goal',
    ),

    path(
        'skill-goal/<int:goal_id>/status/',
        views.update_skill_goal_status,
        name='update_skill_goal_status',
    ),
 path(
     'video/<int:video_id>/sharing/',
     views.update_video_sharing,
     name='update_video_sharing',
 ),
]

urlpatterns += [path('<int:video_id>/camera-view/', views.update_video_camera_view, name='update_camera_view')]
