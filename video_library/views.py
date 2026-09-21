from datetime import datetime, time
from pathlib import Path
import statistics
from django.urls import reverse
from parents_portal.models import ParentAthleteLink

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai import VideoAnalysisProcessor
from .ai.comparison_interpretation import build_coaching_interpretation
from .ai.comparison_service import compare_analyses
from .ai.comparison_summary import build_comparison_summary
from .ai.frame_service import extract_analysis_frames
from .ai.pose_overlay_service import generate_pose_overlay_frames
from .ai.pose_service import analyze_extracted_frames
from .ai.video_service import process_video_file

from .forms import TechniqueProfileForm, VideoUploadForm
from .models import (
    SkillGoal,
    TechniqueProfile,
    Video,
    VideoAnalysis,
    VideoAnalysisFeedback,
    VideoAnalysisMoment,
)

User = get_user_model()

COACH_ROLES = [
    'coach',
    'head_coach',
]

ACTIVE_ANALYSIS_STATUSES = [
    VideoAnalysis.STATUS_QUEUED,
    VideoAnalysis.STATUS_PREPARING,
    VideoAnalysis.STATUS_PROCESSING,
    VideoAnalysis.STATUS_GENERATING_RESULTS,
]


# ============================================================
# ACCESS HELPERS
# ============================================================


def user_is_coach(user):
    return (
        user.is_authenticated
        and user.role in COACH_ROLES
    )


def get_accessible_videos(user):
    """
    Return videos the current coach is allowed to access.
    """
    videos = (
        Video.objects
        .select_related(
            'primary_athlete',
            'uploaded_by',
            'training_group',
            'practice_plan',
        )
        .prefetch_related(
            'tagged_athletes',
        )
    )

    if user.role == 'head_coach':
        return videos

    return (
        videos
        .filter(
            Q(uploaded_by=user)
            | Q(training_group__coaches=user)
            | Q(training_group__isnull=True)
        )
        .distinct()
    )


def user_can_access_analysis(user, analysis):
    return (
        get_accessible_videos(user)
        .filter(id=analysis.video_id)
        .exists()
    )


def get_comparison_candidates(video):
    """
    Completed analyses belonging to another video
    for the same athlete and skill.
    """
    if (
        not video.primary_athlete_id
        or not (video.skill_name or '').strip()
    ):
        return VideoAnalysis.objects.none()

    return (
        VideoAnalysis.objects
        .select_related(
            'video',
            'video__primary_athlete',
        )
        .filter(
            video__primary_athlete_id=video.primary_athlete_id,
            video__skill_name__iexact=video.skill_name.strip(),
            status=VideoAnalysis.STATUS_COMPLETED,
        )
        .exclude(video_id=video.id)
        .order_by('-created_at')
    )
@login_required
@require_POST
def update_video_sharing(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches can update '
                'video sharing.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    video = get_object_or_404(
        get_accessible_videos(
            request.user
        ),
        id=video_id,
    )

    visibility = (
        request.POST.get(
            'visibility',
            '',
        )
        .strip()
    )

    allowed_visibility = {
        Video.VISIBILITY_COACHES,
        Video.VISIBILITY_ATHLETE,
        Video.VISIBILITY_PARENTS,
        Video.VISIBILITY_PRIVATE,
    }

    if (
        visibility
        not in allowed_visibility
    ):
        messages.error(
            request,
            'Choose a valid sharing option.',
        )

        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    video.visibility = (
        visibility
    )

    video.save(
        update_fields=[
            'visibility',
            'updated_at',
        ],
    )

    if (
        visibility
        ==
        Video.VISIBILITY_PARENTS
    ):

        messages.success(
            request,
            (
                'Video is now shared with '
                'the athlete and linked parents.'
            ),
        )

    elif (
        visibility
        ==
        Video.VISIBILITY_ATHLETE
    ):

        messages.success(
            request,
            (
                'Video is now shared with '
                'the athlete.'
            ),
        )

    elif (
        visibility
        ==
        Video.VISIBILITY_COACHES
    ):

        messages.success(
            request,
            (
                'Video is now visible '
                'to coaches only.'
            ),
        )

    else:

        messages.success(
            request,
            (
                'Video is now private '
                'to the uploader.'
            ),
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )

# ============================================================
# VIDEO REFERENCE TOGGLES
# ============================================================


@login_required
@require_POST
def toggle_personal_best(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            'Only coaches can update video references.',
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    video.is_personal_best = not video.is_personal_best

    if video.is_personal_best:
        video.reference_marked_by = request.user
        video.reference_marked_at = timezone.now()

    video.save(
        update_fields=[
            'is_personal_best',
            'reference_marked_by',
            'reference_marked_at',
            'updated_at',
        ],
    )

    messages.success(
        request,
        'Personal Best was updated.',
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


@login_required
@require_POST
def toggle_reference_attempt(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            'Only coaches can update video references.',
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    if (
        not video.primary_athlete_id
        or not (video.skill_name or '').strip()
    ):
        messages.error(
            request,
            (
                'A Reference Attempt requires both '
                'a primary athlete and a skill name.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    if video.is_reference_attempt:
        video.is_reference_attempt = False
        video.save(
            update_fields=[
                'is_reference_attempt',
                'updated_at',
            ],
        )

        messages.success(
            request,
            'Reference Attempt was removed.',
        )

        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    (
        Video.objects
        .filter(
            primary_athlete_id=video.primary_athlete_id,
            skill_name__iexact=video.skill_name.strip(),
            is_reference_attempt=True,
        )
        .exclude(id=video.id)
        .update(is_reference_attempt=False)
    )

    video.is_reference_attempt = True
    video.reference_marked_by = request.user
    video.reference_marked_at = timezone.now()

    video.save(
        update_fields=[
            'is_reference_attempt',
            'reference_marked_by',
            'reference_marked_at',
            'updated_at',
        ],
    )

    messages.success(
        request,
        (
            f'"{video.title}" is now the '
            f'Reference Attempt for {video.skill_name}.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


@login_required
@require_POST
def toggle_coaching_example(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            'Only coaches can update video references.',
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    video.is_coaching_example = not video.is_coaching_example

    if video.is_coaching_example:
        video.reference_marked_by = request.user
        video.reference_marked_at = timezone.now()

    video.save(
        update_fields=[
            'is_coaching_example',
            'reference_marked_by',
            'reference_marked_at',
            'updated_at',
        ],
    )

    messages.success(
        request,
        'Coaching Example was updated.',
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# DASHBOARD
# ============================================================
@login_required
def family_video_library(request):
    """
    Read-only video library for athletes and approved parents.

    Athletes can see videos published to athletes or parents.
    Parents can see only videos published to parents for an
    athlete connected through an approved parent link.
    """

    user = request.user

    if user.role not in [
        'athlete',
        'parent',
    ]:
        messages.error(
            request,
            (
                'This video library is available only '
                'to athletes and parents.'
            )
        )

        return redirect(
            'role_redirect'
        )

    available_athletes = []
    selected_athlete = None

    # ---------------------------------------------------------
    # Athlete access
    # ---------------------------------------------------------

    if user.role == 'athlete':
        available_athletes = [
            user
        ]

        selected_athlete = user

        allowed_visibilities = [
            Video.VISIBILITY_ATHLETE,
            Video.VISIBILITY_PARENTS,
        ]

    # ---------------------------------------------------------
    # Parent access
    # ---------------------------------------------------------

    else:
        approved_links = (
            ParentAthleteLink.objects
            .filter(
                parent=user,
                approved=True
            )
            .select_related('athlete')
            .order_by(
                'athlete__first_name',
                'athlete__last_name',
                'athlete__username'
            )
        )

        available_athletes = [
            link.athlete
            for link in approved_links
        ]

        selected_athlete_id = request.GET.get(
            'athlete'
        )

        if available_athletes:
            if selected_athlete_id:
                selected_athlete = next(
                    (
                        athlete
                        for athlete in available_athletes
                        if str(athlete.id) == selected_athlete_id
                    ),
                    None
                )

                if selected_athlete is None:
                    messages.error(
                        request,
                        (
                            'You do not have permission to view '
                            'videos for that athlete.'
                        )
                    )

                    return redirect(
                        'video_library:family_library'
                    )

            else:
                selected_athlete = available_athletes[0]

        allowed_visibilities = [
            Video.VISIBILITY_PARENTS,
        ]

    # ---------------------------------------------------------
    # Accessible videos
    # ---------------------------------------------------------

    if selected_athlete:
        videos = (
            Video.objects
            .filter(
                Q(primary_athlete=selected_athlete)
                | Q(tagged_athletes=selected_athlete),
                status=Video.STATUS_READY,
                visibility__in=allowed_visibilities
            )
            .select_related(
                'primary_athlete',
                'uploaded_by',
                'training_group',
                'practice_plan'
            )
            .prefetch_related(
                'tagged_athletes'
            )
            .distinct()
            .order_by(
                '-recorded_at',
                '-uploaded_at'
            )
        )

    else:
        videos = Video.objects.none()

    return render(
        request,
        'video_library/family_video_library.html',
        {
            'videos': videos,
            'video_count': videos.count(),
            'available_athletes': available_athletes,
            'selected_athlete': selected_athlete,
        }
    )

@login_required
def video_dashboard(request):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )
        return redirect('role_redirect')

    accessible_videos = get_accessible_videos(request.user)

    recent_videos = (
        accessible_videos
        .filter(status=Video.STATUS_READY)
        .order_by('-uploaded_at')[:12]
    )

    context = {
        'recent_videos': recent_videos,
        'total_video_count': (
            accessible_videos
            .exclude(status=Video.STATUS_ARCHIVED)
            .count()
        ),
        'favorite_count': (
            accessible_videos
            .filter(
                is_favorite=True,
                status=Video.STATUS_READY,
            )
            .count()
        ),
        'pending_ai_count': (
            accessible_videos
            .filter(
                ai_status__in=[
                    Video.AI_QUEUED,
                    Video.AI_PROCESSING,
                ],
            )
            .count()
        ),
    }

    return render(
        request,
        'video_library/dashboard.html',
        context,
    )


# ============================================================
# VIDEO LIST
# ============================================================


@login_required
def video_list(request):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )
        return redirect('role_redirect')

    videos = (
        get_accessible_videos(request.user)
        .exclude(status=Video.STATUS_ARCHIVED)
    )

    search_query = request.GET.get('search', '').strip()
    athlete_filter = request.GET.get('athlete', '').strip()
    event_filter = request.GET.get('event', '').strip()
    type_filter = request.GET.get('video_type', '').strip()
    favorite_filter = request.GET.get('favorites', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search_query:
        videos = (
            videos
            .filter(
                Q(title__icontains=search_query)
                | Q(skill_name__icontains=search_query)
                | Q(tags__icontains=search_query)
                | Q(notes__icontains=search_query)
                | Q(primary_athlete__username__icontains=search_query)
                | Q(primary_athlete__first_name__icontains=search_query)
                | Q(primary_athlete__last_name__icontains=search_query)
                | Q(tagged_athletes__username__icontains=search_query)
                | Q(tagged_athletes__first_name__icontains=search_query)
                | Q(tagged_athletes__last_name__icontains=search_query)
            )
            .distinct()
        )

    if athlete_filter:
        videos = (
            videos
            .filter(
                Q(primary_athlete_id=athlete_filter)
                | Q(tagged_athletes__id=athlete_filter)
            )
            .distinct()
        )

    if event_filter:
        videos = videos.filter(event=event_filter)

    if type_filter:
        videos = videos.filter(video_type=type_filter)

    if favorite_filter == 'yes':
        videos = videos.filter(is_favorite=True)

    if date_from:
        videos = videos.filter(
            recorded_at__date__gte=date_from,
        )

    if date_to:
        videos = videos.filter(
            recorded_at__date__lte=date_to,
        )

    videos = videos.order_by(
        '-recorded_at',
        '-uploaded_at',
    )

    athletes = (
        User.objects
        .filter(
            role='athlete',
            is_active=True,
        )
        .order_by(
            'first_name',
            'last_name',
            'username',
        )
    )

    context = {
        'videos': videos,
        'athletes': athletes,
        'event_choices': Video.EVENT_CHOICES,
        'video_type_choices': Video.VIDEO_TYPE_CHOICES,
        'search_query': search_query,
        'athlete_filter': athlete_filter,
        'event_filter': event_filter,
        'type_filter': type_filter,
        'favorite_filter': favorite_filter,
        'date_from': date_from,
        'date_to': date_to,
        'result_count': videos.count(),
    }

    return render(
        request,
        'video_library/video_list.html',
        context,
    )


# ============================================================
# VIDEO DETAIL
# ============================================================


@login_required
def video_detail(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user)
        .prefetch_related(
            'reviews__assigned_coach',
        ),
        id=video_id,
    )

    related_videos = (
        get_accessible_videos(request.user)
        .exclude(id=video.id)
        .exclude(status=Video.STATUS_ARCHIVED)
    )

    if video.primary_athlete_id:
        related_videos = related_videos.filter(
            primary_athlete=video.primary_athlete,
        )
    else:
        related_videos = related_videos.none()

    if video.event:
        related_videos = related_videos.filter(
            event=video.event,
        )

    related_videos = related_videos.order_by(
        '-recorded_at',
        '-uploaded_at',
    )[:6]

    latest_analysis = (
        video.analyses
        .select_related(
            'reviewed_by',
            'requested_by',
        )
        .prefetch_related(
            'moments',
            'feedback_entries',
        )
        .order_by('-created_at')
        .first()
    )

    analysis_moment_items = []

    if latest_analysis:
        coach_feedback = {
            feedback.moment_id: feedback
            for feedback in (
                latest_analysis
                .feedback_entries
                .filter(
                    coach=request.user,
                    moment__isnull=False,
                )
                .select_related('moment')
            )
        }

        analysis_moment_items = [
            {
                'moment': moment,
                'feedback': coach_feedback.get(moment.id),
            }
            for moment in latest_analysis.moments.all()
        ]

    context = {
        'video': video,
        'related_videos': related_videos,
        'latest_analysis': latest_analysis,
        'analysis_moment_items': analysis_moment_items,
        'analysis_count': video.analyses.count(),
        'comparison_candidates': get_comparison_candidates(video),
    }

    return render(
        request,
        'video_library/video_detail.html',
        context,
    )


# ============================================================
# VIDEO UPLOAD
# ============================================================


@login_required
def video_upload(request):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'upload videos.'
            ),
        )
        return redirect('role_redirect')

    if request.method == 'POST':
        form = VideoUploadForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            uploaded_files = form.cleaned_data['videos']
            uploaded_videos = []

            with transaction.atomic():
                for index, uploaded_file in enumerate(
                    uploaded_files,
                    start=1,
                ):
                    original_stem = Path(
                        uploaded_file.name
                    ).stem

                    title_prefix = (
                        form.cleaned_data[
                            'title_prefix'
                        ]
                        .strip()
                    )

                    if title_prefix:
                        if len(uploaded_files) > 1:
                            title = (
                                f'{title_prefix} '
                                f'{index}'
                            )
                        else:
                            title = title_prefix
                    else:
                        title = (
                            original_stem
                            or f'Video {index}'
                        )

                    recorded_at = None
                    recorded_date = (
                        form.cleaned_data[
                            'recorded_date'
                        ]
                    )

                    if recorded_date:
                        recorded_at = (
                            timezone.make_aware(
                                datetime.combine(
                                    recorded_date,
                                    time.min,
                                )
                            )
                        )

                    ai_status = (
                        Video.AI_QUEUED
                        if form.cleaned_data[
                            'request_ai_analysis'
                        ]
                        else Video.AI_NOT_REQUESTED
                    )

                    video = Video.objects.create(
                        title=title,
                        video_file=uploaded_file,
                        primary_athlete=(
                            form.cleaned_data[
                                'primary_athlete'
                            ]
                        ),
                        training_group=(
                            form.cleaned_data[
                                'training_group'
                            ]
                        ),
                        practice_plan=(
                            form.cleaned_data[
                                'practice_plan'
                            ]
                        ),
                        event=(
                            form.cleaned_data[
                                'event'
                            ]
                        ),
                        skill_name=(
                            form.cleaned_data[
                                'skill_name'
                            ].strip()
                        ),
                        video_type=(
                            form.cleaned_data[
                                'video_type'
                            ]
                        ),
                        recorded_at=recorded_at,
                        notes=(
                            form.cleaned_data[
                                'notes'
                            ].strip()
                        ),
                        tags=(
                            form.cleaned_data[
                                'tags'
                            ].strip()
                        ),
                        visibility=(
                            form.cleaned_data[
                                'visibility'
                            ]
                        ),
                        is_favorite=(
                            form.cleaned_data[
                                'mark_as_favorite'
                            ]
                        ),
                        uploaded_by=request.user,
                        original_filename=(
                            uploaded_file.name
                        ),
                        content_type=getattr(
                            uploaded_file,
                            'content_type',
                            '',
                        ),
                        ai_status=ai_status,
                        status=Video.STATUS_UPLOADING,
                    )

                    video.tagged_athletes.set(
                        form.cleaned_data[
                            'tagged_athletes'
                        ]
                    )

                    uploaded_videos.append(video)

            video_count = len(uploaded_videos)

            messages.success(
                request,
                (
                    f'{video_count} '
                    f'video'
                    f'{"s" if video_count != 1 else ""} '
                    'uploaded and queued for MP4 conversion.'
                ),
            )

            return redirect(
                'video_library:dashboard'
            )

    else:
        form = VideoUploadForm(
            user=request.user,
        )

    return render(
        request,
        'video_library/upload.html',
        {'form': form},
    )


# ============================================================
# FAVORITE VIDEO
# ============================================================


@login_required
@require_POST
def toggle_video_favorite(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'update this video.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    video.is_favorite = not video.is_favorite

    video.save(
        update_fields=[
            'is_favorite',
            'updated_at',
        ],
    )

    if video.is_favorite:
        messages.success(
            request,
            f'"{video.title}" was added to favorites.',
        )
    else:
        messages.success(
            request,
            f'"{video.title}" was removed from favorites.',
        )

    next_url = request.POST.get('next')

    if next_url:
        return redirect(next_url)

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# VIDEO METADATA
# ============================================================


@login_required
@require_POST
def process_video_metadata(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'process this video.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    try:
        process_video_file(video)

        messages.success(
            request,
            (
                'Video metadata and thumbnail '
                'were generated successfully.'
            ),
        )

    except Exception as error:
        messages.error(
            request,
            (
                'Video processing failed: '
                f'{error}'
            ),
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# REQUEST ANALYSIS
# ============================================================


@login_required
@require_POST
def request_video_analysis(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'analyze this video.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    active_analysis = (
        video.analyses
        .filter(
            status__in=ACTIVE_ANALYSIS_STATUSES,
        )
        .order_by('-created_at')
        .first()
    )

    if active_analysis:
        messages.info(
            request,
            (
                'This video already has an '
                'analysis in progress.'
            ),
        )

        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    VideoAnalysis.objects.create(
        video=video,
        requested_by=request.user,
        status=VideoAnalysis.STATUS_QUEUED,
        progress_percentage=0,
        current_step='Waiting to begin',
        analysis_source=VideoAnalysis.SOURCE_MOCK,
        analysis_version='0.1.0',
        requested_skill=video.skill_name,
    )

    video.ai_status = Video.AI_QUEUED
    video.save(
        update_fields=[
            'ai_status',
            'updated_at',
        ],
    )

    messages.success(
        request,
        'Video analysis was added to the queue.',
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# RERUN ANALYSIS
# ============================================================


@login_required
@require_POST
def rerun_video_analysis(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'analyze this video.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    active_analysis = (
        video.analyses
        .filter(
            status__in=ACTIVE_ANALYSIS_STATUSES,
        )
        .order_by('-created_at')
        .first()
    )

    if active_analysis:
        messages.info(
            request,
            (
                'This video already has an '
                'analysis in progress.'
            ),
        )

        return redirect(
            'video_library:analysis_detail',
            analysis_id=active_analysis.id,
        )

    latest_analysis = (
        video.analyses
        .order_by('-created_at')
        .first()
    )

    requested_skill = (
        video.skill_name
        or ''
    ).strip()

    if not requested_skill and latest_analysis:
        requested_skill = (
            latest_analysis.requested_skill
            or latest_analysis.detected_skill
            or ''
        )

    VideoAnalysis.objects.create(
        video=video,
        requested_by=request.user,
        status=VideoAnalysis.STATUS_QUEUED,
        progress_percentage=0,
        current_step='Waiting to begin',
        analysis_source=VideoAnalysis.SOURCE_MOCK,
        analysis_version='0.1.0',
        requested_skill=requested_skill,
    )

    video.ai_status = Video.AI_QUEUED
    video.save(
        update_fields=[
            'ai_status',
            'updated_at',
        ],
    )

    messages.success(
        request,
        (
            'A new analysis was created. '
            'Previous results and coach reviews '
            'were preserved.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# PROCESS ANALYSIS
# ============================================================


@login_required
@require_POST
def process_mock_analysis(request, analysis_id):
    if not user_is_coach(request.user):
        return JsonResponse(
            {'error': 'Permission denied.'},
            status=403,
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects.select_related('video'),
        id=analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        analysis,
    ):
        return JsonResponse(
            {'error': 'Permission denied.'},
            status=403,
        )

    if analysis.is_finished:
        return JsonResponse({
            'status': analysis.status,
            'status_display': (
                analysis.get_status_display()
            ),
            'progress_percentage': (
                analysis.progress_percentage
            ),
            'current_step': analysis.current_step,
            'is_finished': True,
        })

    try:
        processor = VideoAnalysisProcessor()
        processor.process(analysis=analysis)

    except Exception as error:
        analysis.refresh_from_db()

        return JsonResponse(
            {
                'status': analysis.status,
                'status_display': (
                    analysis.get_status_display()
                ),
                'progress_percentage': (
                    analysis.progress_percentage
                ),
                'current_step': (
                    analysis.current_step
                ),
                'is_finished': analysis.is_finished,
                'error': str(error),
            },
            status=500,
        )

    analysis.refresh_from_db()

    return JsonResponse({
        'status': analysis.status,
        'status_display': (
            analysis.get_status_display()
        ),
        'progress_percentage': (
            analysis.progress_percentage
        ),
        'current_step': analysis.current_step,
        'is_finished': analysis.is_finished,
    })


# ============================================================
# ANALYSIS STATUS
# ============================================================


@login_required
def video_analysis_status(request, analysis_id):
    if not user_is_coach(request.user):
        return JsonResponse(
            {'error': 'Permission denied.'},
            status=403,
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects.select_related('video'),
        id=analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        analysis,
    ):
        return JsonResponse(
            {'error': 'Permission denied.'},
            status=403,
        )

    return JsonResponse({
        'analysis_id': analysis.id,
        'status': analysis.status,
        'status_display': (
            analysis.get_status_display()
        ),
        'progress_percentage': (
            analysis.progress_percentage
        ),
        'current_step': analysis.current_step,
        'is_finished': analysis.is_finished,
        'detail_url': (
            request.build_absolute_uri(
                redirect(
                    'video_library:video_detail',
                    video_id=analysis.video_id,
                ).url
            )
        ),
    })


# ============================================================
# ANALYSIS HISTORY
# ============================================================


@login_required
def video_analysis_history(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'view analysis history.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    analyses = (
        video.analyses
        .select_related(
            'requested_by',
            'reviewed_by',
        )
        .prefetch_related(
            'moments',
            'feedback_entries',
        )
        .order_by('-created_at')
    )

    active_analysis = (
        analyses
        .filter(
            status__in=ACTIVE_ANALYSIS_STATUSES,
        )
        .first()
    )

    context = {
        'video': video,
        'analyses': analyses,
        'analysis_count': analyses.count(),
        'active_analysis': active_analysis,
    }

    return render(
        request,
        'video_library/analysis_history.html',
        context,
    )


# ============================================================
# ANALYSIS DETAIL
# ============================================================


@login_required
def video_analysis_detail(request, analysis_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'view this analysis.'
            ),
        )
        return redirect('role_redirect')

    analysis = get_object_or_404(
        VideoAnalysis.objects
        .select_related(
            'video',
            'video__primary_athlete',
            'requested_by',
            'reviewed_by',
        )
        .prefetch_related(
            'moments',
            'feedback_entries',
        ),
        id=analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        analysis,
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'view this analysis.'
            ),
        )
        return redirect(
            'video_library:video_list'
        )

    coach_feedback = {
        feedback.moment_id: feedback
        for feedback in (
            analysis
            .feedback_entries
            .filter(
                coach=request.user,
                moment__isnull=False,
            )
            .select_related('moment')
        )
    }

    analysis_moment_items = [
        {
            'moment': moment,
            'feedback': coach_feedback.get(
                moment.id
            ),
        }
        for moment in analysis.moments.all()
    ]

    previous_analysis = (
        analysis.video.analyses
        .filter(
            created_at__lt=analysis.created_at,
        )
        .order_by('-created_at')
        .first()
    )

    next_analysis = (
        analysis.video.analyses
        .filter(
            created_at__gt=analysis.created_at,
        )
        .order_by('created_at')
        .first()
    )

    context = {
        'video': analysis.video,
        'analysis': analysis,
        'analysis_moment_items': (
            analysis_moment_items
        ),
        'previous_analysis': previous_analysis,
        'next_analysis': next_analysis,
        'comparison_candidates': (
            get_comparison_candidates(
                analysis.video
            )
        ),
    }

    return render(
        request,
        'video_library/analysis_detail.html',
        context,
    )


# ============================================================
# REVIEW ANALYSIS
# ============================================================


@login_required
@require_POST
def review_video_analysis(request, analysis_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this analysis.'
            ),
        )
        return redirect('role_redirect')

    analysis = get_object_or_404(
        VideoAnalysis.objects.select_related(
            'video',
        ),
        id=analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        analysis,
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this analysis.'
            ),
        )
        return redirect(
            'video_library:video_list'
        )

    if (
        analysis.status
        != VideoAnalysis.STATUS_COMPLETED
    ):
        messages.error(
            request,
            (
                'Only completed analyses can '
                'be reviewed.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=analysis.video_id,
        )

    review_status = (
        request.POST.get(
            'review_status',
            '',
        )
        .strip()
    )

    review_notes = (
        request.POST.get(
            'coach_review_notes',
            '',
        )
        .strip()
    )

    allowed_statuses = {
        VideoAnalysis.REVIEW_APPROVED,
        VideoAnalysis.REVIEW_PARTIAL,
        VideoAnalysis.REVIEW_REJECTED,
    }

    if review_status not in allowed_statuses:
        messages.error(
            request,
            'Choose a valid review decision.',
        )
        return redirect(
            'video_library:video_detail',
            video_id=analysis.video_id,
        )

    analysis.review_status = review_status
    analysis.coach_review_notes = review_notes
    analysis.reviewed_by = request.user
    analysis.reviewed_at = timezone.now()

    analysis.save(
        update_fields=[
            'review_status',
            'coach_review_notes',
            'reviewed_by',
            'reviewed_at',
            'updated_at',
        ],
    )

    messages.success(
        request,
        'Your analysis review was saved.',
    )

    return redirect(
        'video_library:video_detail',
        video_id=analysis.video_id,
    )


# ============================================================
# REVIEW ANALYSIS MOMENT
# ============================================================


@login_required
@require_POST
def review_analysis_moment(request, moment_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this observation.'
            ),
        )
        return redirect('role_redirect')

    moment = get_object_or_404(
        VideoAnalysisMoment.objects.select_related(
            'analysis__video',
        ),
        id=moment_id,
    )

    analysis = moment.analysis

    if not user_can_access_analysis(
        request.user,
        analysis,
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this observation.'
            ),
        )
        return redirect(
            'video_library:video_list'
        )

    if (
        analysis.status
        != VideoAnalysis.STATUS_COMPLETED
    ):
        messages.error(
            request,
            (
                'Only completed analyses '
                'can receive feedback.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=analysis.video_id,
        )

    rating = (
        request.POST.get(
            'rating',
            '',
        )
        .strip()
    )

    comment = (
        request.POST.get(
            'comment',
            '',
        )
        .strip()
    )

    allowed_ratings = {
        VideoAnalysisFeedback.RATING_CORRECT,
        VideoAnalysisFeedback.RATING_PARTIAL,
        VideoAnalysisFeedback.RATING_INCORRECT,
    }

    if rating not in allowed_ratings:
        messages.error(
            request,
            'Choose a valid feedback rating.',
        )
        return redirect(
            'video_library:video_detail',
            video_id=analysis.video_id,
        )

    VideoAnalysisFeedback.objects.update_or_create(
        analysis=analysis,
        moment=moment,
        coach=request.user,
        defaults={
            'rating': rating,
            'comment': comment,
        },
    )

    messages.success(
        request,
        (
            f'Feedback for "{moment.label}" '
            'was saved.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=analysis.video_id,
    )


# ============================================================
# FRAME EXTRACTION
# ============================================================


@login_required
@require_POST
def extract_video_analysis_frames(
    request,
    video_id,
):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission to '
                'extract frames from this video.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    analysis = (
        video.analyses
        .order_by('-created_at')
        .first()
    )

    if not analysis:
        messages.error(
            request,
            (
                'Run an analysis first so the '
                'extracted frames have an analysis '
                'record to belong to.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    try:
        frames = extract_analysis_frames(
            analysis=analysis,
            sample_count=None,
        )

        messages.success(
            request,
            (
                f'{len(frames)} real video '
                'frames were extracted successfully.'
            ),
        )

    except Exception as error:
        messages.error(
            request,
            (
                'Frame extraction failed: '
                f'{error}'
            ),
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# POSE DETECTION
# ============================================================


@login_required
@require_POST
def detect_video_pose(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission '
                'to run pose detection.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    analysis = (
        video.analyses
        .order_by('-created_at')
        .first()
    )

    if not analysis:
        messages.error(
            request,
            (
                'Run an analysis before '
                'running pose detection.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    frame_count = (
        analysis.moments
        .exclude(frame_image='')
        .count()
    )

    if frame_count == 0:
        messages.error(
            request,
            (
                'Extract real analysis frames '
                'before running pose detection.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    try:
        results = analyze_extracted_frames(
            analysis
        )

        messages.success(
            request,
            (
                'Pose detection completed. '
                f'{results["frames_with_pose"]} of '
                f'{results["analyzed_frames"]} frames '
                'contained a detected pose.'
            ),
        )

    except Exception as error:
        messages.error(
            request,
            (
                'Pose detection failed: '
                f'{error}'
            ),
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# POSE OVERLAYS
# ============================================================


@login_required
@require_POST
def generate_pose_overlays(request, video_id):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'You do not have permission '
                'to generate pose overlays.'
            ),
        )
        return redirect('role_redirect')

    video = get_object_or_404(
        get_accessible_videos(request.user),
        id=video_id,
    )

    analysis = (
        video.analyses
        .order_by('-created_at')
        .first()
    )

    if not analysis:
        messages.error(
            request,
            'Run an analysis first.',
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    pose_frame_count = 0

    for moment in analysis.moments.all():
        measurements = moment.measurements or {}

        if measurements.get(
            'pose_landmarks'
        ):
            pose_frame_count += 1

    if pose_frame_count == 0:
        messages.error(
            request,
            (
                'Run pose detection before '
                'generating overlays.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    try:
        result = generate_pose_overlay_frames(
            analysis
        )

        messages.success(
            request,
            (
                f'{result["generated_frames"]} '
                'annotated pose frames were generated.'
            ),
        )

    except Exception as error:
        messages.error(
            request,
            (
                'Pose overlay generation failed: '
                f'{error}'
            ),
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


# ============================================================
# ANALYSIS COMPARISON
# ============================================================


@login_required
def compare_video_analyses(
    request,
    first_analysis_id,
    second_analysis_id,
):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches '
                'can compare analyses.'
            ),
        )
        return redirect('role_redirect')

    first_analysis = get_object_or_404(
        VideoAnalysis.objects.select_related(
            'video',
            'video__primary_athlete',
        ),
        id=first_analysis_id,
    )

    second_analysis = get_object_or_404(
        VideoAnalysis.objects.select_related(
            'video',
            'video__primary_athlete',
        ),
        id=second_analysis_id,
    )

    if (
        not user_can_access_analysis(
            request.user,
            first_analysis,
        )
        or not user_can_access_analysis(
            request.user,
            second_analysis,
        )
    ):
        messages.error(
            request,
            (
                'You do not have permission '
                'to compare these analyses.'
            ),
        )
        return redirect(
            'video_library:video_list'
        )

    comparison = compare_analyses(
        first_analysis=first_analysis,
        second_analysis=second_analysis,
    )

    context = {
        'first_analysis': first_analysis,
        'second_analysis': second_analysis,
        'phase_comparisons': (
            comparison[
                'phase_comparisons'
            ]
        ),
    }

    return render(
        request,
        'video_library/analysis_comparison.html',
        context,
    )


@login_required
@require_POST
def start_analysis_comparison(
    request,
    first_analysis_id,
):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches '
                'can compare video analyses.'
            ),
        )
        return redirect('role_redirect')

    first_analysis = get_object_or_404(
        VideoAnalysis.objects.select_related(
            'video',
            'video__primary_athlete',
        ),
        id=first_analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        first_analysis,
    ):
        messages.error(
            request,
            (
                'You do not have permission '
                'to compare this analysis.'
            ),
        )
        return redirect(
            'video_library:video_list'
        )

    second_analysis_id = request.POST.get(
        'second_analysis_id'
    )

    if not second_analysis_id:
        messages.error(
            request,
            'Choose an attempt to compare.',
        )
        return redirect(
            'video_library:video_detail',
            video_id=first_analysis.video_id,
        )

    second_analysis = get_object_or_404(
        VideoAnalysis.objects.select_related(
            'video',
            'video__primary_athlete',
        ),
        id=second_analysis_id,
    )

    if not user_can_access_analysis(
        request.user,
        second_analysis,
    ):
        messages.error(
            request,
            (
                'You do not have permission '
                'to compare that analysis.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=first_analysis.video_id,
        )

    if (
        first_analysis.video.primary_athlete_id
        != second_analysis.video.primary_athlete_id
    ):
        messages.error(
            request,
            (
                'These attempts belong '
                'to different athletes.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=first_analysis.video_id,
        )

    first_skill = (
        first_analysis.video.skill_name
        or ''
    ).strip().lower()

    second_skill = (
        second_analysis.video.skill_name
        or ''
    ).strip().lower()

    if (
        not first_skill
        or first_skill != second_skill
    ):
        messages.error(
            request,
            (
                'Attempts must use the same '
                'skill before they can be compared.'
            ),
        )
        return redirect(
            'video_library:video_detail',
            video_id=first_analysis.video_id,
        )

    return redirect(
        'video_library:compare_analyses',
        first_analysis_id=first_analysis.id,
        second_analysis_id=second_analysis.id,
    )


# ============================================================
# VIDEO COMPARISON
# ============================================================


@login_required
def video_compare(request):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches '
                'can compare videos.'
            ),
        )
        return redirect('role_redirect')

    first_video_id = (
        request.GET.get(
            'video_1',
            '',
        )
        .strip()
    )

    second_video_id = (
        request.GET.get(
            'video_2',
            '',
        )
        .strip()
    )

    if (
        not first_video_id
        or not second_video_id
    ):
        messages.error(
            request,
            'Select two videos to compare.',
        )
        return redirect(
            'video_library:video_list'
        )

    if first_video_id == second_video_id:
        messages.error(
            request,
            'Select two different videos.',
        )
        return redirect(
            'video_library:video_list'
        )

    accessible_videos = get_accessible_videos(
        request.user
    )

    first_video = get_object_or_404(
        accessible_videos,
        id=first_video_id,
    )

    second_video = get_object_or_404(
        accessible_videos,
        id=second_video_id,
    )

    shared_athlete = None

    if (
        first_video.primary_athlete_id
        and first_video.primary_athlete_id
        == second_video.primary_athlete_id
    ):
        shared_athlete = (
            first_video.primary_athlete
        )

    first_analysis = (
        first_video.analyses
        .filter(
            status=VideoAnalysis.STATUS_COMPLETED,
        )
        .prefetch_related('moments')
        .order_by('-created_at')
        .first()
    )

    second_analysis = (
        second_video.analyses
        .filter(
            status=VideoAnalysis.STATUS_COMPLETED,
        )
        .prefetch_related('moments')
        .order_by('-created_at')
        .first()
    )

    phase_order = [
        'setup',
        'entry',
        'main_action',
        'peak',
        'exit',
        'finish',
    ]

    def build_phase_map(analysis):
        phase_map = {}

        if not analysis:
            return phase_map

        moments = list(
            analysis.moments
            .exclude(frame_image='')
            .order_by('timestamp_seconds')
        )

        for phase in phase_order:
            candidates = []

            for moment in moments:
                measurements = (
                    moment.measurements
                    or {}
                )

                if (
                    measurements.get(
                        'skill_phase'
                    )
                    != phase
                ):
                    continue

                candidates.append(moment)

            if not candidates:
                continue

            key_candidates = [
                moment
                for moment in candidates
                if (
                    moment.measurements
                    or {}
                ).get(
                    'is_key_frame'
                )
            ]

            available = (
                key_candidates
                or candidates
            )

            best_moment = max(
                available,
                key=lambda moment: float(
                    (
                        moment.measurements
                        or {}
                    ).get(
                        'frame_quality_score'
                    )
                    or 0.0
                ),
            )

            measurements = (
                best_moment.measurements
                or {}
            )

            gymnastics = (
                measurements.get(
                    'gymnastics_measurements'
                )
                or {}
            )

            def get_angle(section):
                data = (
                    gymnastics.get(section)
                    or {}
                )

                return data.get(
                    'average_angle'
                )

            phase_map[phase] = {
                'timestamp': float(
                    best_moment.timestamp_seconds
                ),
                'moment_id': best_moment.id,
                'frame_number': (
                    measurements.get(
                        'frame_number'
                    )
                ),
                'frame_score': (
                    measurements.get(
                        'frame_quality_score'
                    )
                ),
                'knee_angle': get_angle(
                    'knee_extension'
                ),
                'hip_angle': get_angle(
                    'hip_position'
                ),
                'shoulder_angle': get_angle(
                    'shoulder_position'
                ),
                'elbow_angle': get_angle(
                    'elbow_extension'
                ),
            }

        return phase_map

    first_phase_map = build_phase_map(
        first_analysis
    )

    second_phase_map = build_phase_map(
        second_analysis
    )

    phase_comparisons = []

    for phase in phase_order:
        first_phase = first_phase_map.get(
            phase
        )
        second_phase = second_phase_map.get(
            phase
        )

        if (
            not first_phase
            and not second_phase
        ):
            continue

        phase_comparisons.append({
            'name': phase,
            'label': (
                phase
                .replace('_', ' ')
                .title()
            ),
            'first': first_phase,
            'second': second_phase,
        })

    comparison_summary = (
        build_comparison_summary(
            phase_comparisons
        )
    )

    comparison_skill_name = (
        first_video.skill_name
        or (
            first_analysis.requested_skill
            if first_analysis
            else ''
        )
        or (
            first_analysis.detected_skill
            if first_analysis
            else ''
        )
        or second_video.skill_name
        or (
            second_analysis.requested_skill
            if second_analysis
            else ''
        )
        or (
            second_analysis.detected_skill
            if second_analysis
            else ''
        )
        or ''
    ).strip()

    coaching_interpretation = (
        build_coaching_interpretation(
            skill_name=comparison_skill_name,
            phase_comparisons=phase_comparisons,
        )
    )

    context = {
        'first_video': first_video,
        'second_video': second_video,
        'shared_athlete': shared_athlete,
        'first_analysis': first_analysis,
        'second_analysis': second_analysis,
        'phase_comparisons': phase_comparisons,
        'comparison_summary': comparison_summary,
        'comparison_skill_name': (
            comparison_skill_name
        ),
        'coaching_interpretation': (
            coaching_interpretation
        ),
    }

    return render(
        request,
        'video_library/video_compare.html',
        context,
    )


# ============================================================
# ATHLETE COMPARE SELECTOR
# ============================================================


@login_required
def athlete_video_compare_select(
    request,
    athlete_id,
):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches '
                'can compare athlete videos.'
            ),
        )
        return redirect('role_redirect')

    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )

    videos = (
        get_accessible_videos(request.user)
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(status=Video.STATUS_ARCHIVED)
        .distinct()
    )

    event_filter = (
        request.GET.get(
            'event',
            '',
        )
        .strip()
    )

    skill_filter = (
        request.GET.get(
            'skill',
            '',
        )
        .strip()
    )

    if event_filter:
        videos = videos.filter(
            event=event_filter,
        )

    if skill_filter:
        videos = videos.filter(
            skill_name__iexact=skill_filter,
        )

    reference_video = (
        videos
        .filter(
            is_reference_attempt=True,
        )
        .first()
    )

    videos = videos.order_by(
        '-is_reference_attempt',
        '-recorded_at',
        '-uploaded_at',
    )

    skill_names = (
        get_accessible_videos(request.user)
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(skill_name='')
        .values_list(
            'skill_name',
            flat=True,
        )
        .distinct()
        .order_by('skill_name')
    )

    context = {
        'athlete': athlete,
        'videos': videos,
        'event_choices': Video.EVENT_CHOICES,
        'event_filter': event_filter,
        'skill_filter': skill_filter,
        'skill_names': skill_names,
        'reference_video': reference_video,
        'result_count': videos.count(),
    }

    return render(
        request,
        'video_library/compare_select.html',
        context,
    )


# ============================================================
# ATHLETE VIDEO TIMELINE
# ============================================================


@login_required
def athlete_video_timeline(
    request,
    athlete_id,
):
    if not user_is_coach(request.user):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access athlete video timelines.'
            ),
        )
        return redirect('role_redirect')

    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )

    videos = (
        get_accessible_videos(request.user)
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(status=Video.STATUS_ARCHIVED)
        .distinct()
        .order_by(
            '-recorded_at',
            '-uploaded_at',
        )
    )

    event_sections = []

    for event_value, event_label in (
        Video.EVENT_CHOICES
    ):
        event_videos = [
            video
            for video in videos
            if video.event == event_value
        ]

        if event_videos:
            event_sections.append({
                'value': event_value,
                'label': event_label,
                'videos': event_videos,
                'count': len(event_videos),
            })

    skill_names = sorted({
        video.skill_name.strip()
        for video in videos
        if (
            video.skill_name
            and video.skill_name.strip()
        )
    })

    context = {
        'athlete': athlete,
        'videos': videos,
        'event_sections': event_sections,
        'total_video_count': videos.count(),
        'favorite_count': (
            videos
            .filter(is_favorite=True)
            .count()
        ),
        'event_count': len(event_sections),
        'skill_count': len(skill_names),
        'skill_names': skill_names,
    }

    return render(
        request,
        'video_library/athlete_timeline.html',
        context,
    )


# ============================================================
# TECHNIQUE PROFILES
# ============================================================


@login_required
def technique_profile_list(request):
    if request.user.role != 'head_coach':
        messages.error(
            request,
            (
                'Only head coaches can '
                'manage technique profiles.'
            ),
        )
        return redirect(
            'video_library:dashboard'
        )

    profiles = (
        TechniqueProfile.objects
        .order_by('skill_name')
    )

    return render(
        request,
        'video_library/technique_profile_list.html',
        {'profiles': profiles},
    )


@login_required
def technique_profile_create(request):
    if request.user.role != 'head_coach':
        messages.error(
            request,
            (
                'Only head coaches can '
                'manage technique profiles.'
            ),
        )
        return redirect(
            'video_library:dashboard'
        )

    if request.method == 'POST':
        form = TechniqueProfileForm(
            request.POST
        )

        if form.is_valid():
            profile = form.save(
                commit=False
            )
            profile.created_by = request.user
            profile.updated_by = request.user
            profile.save()

            messages.success(
                request,
                'Technique profile was created.',
            )

            return redirect(
                'video_library:technique_profile_list'
            )

    else:
        form = TechniqueProfileForm()

    return render(
        request,
        'video_library/technique_profile_form.html',
        {
            'form': form,
            'profile': None,
        },
    )


@login_required
def technique_profile_edit(
    request,
    profile_id,
):
    if request.user.role != 'head_coach':
        messages.error(
            request,
            (
                'Only head coaches can '
                'manage technique profiles.'
            ),
        )
        return redirect(
            'video_library:dashboard'
        )

    profile = get_object_or_404(
        TechniqueProfile,
        id=profile_id,
    )

    if request.method == 'POST':
        form = TechniqueProfileForm(
            request.POST,
            instance=profile,
        )

        if form.is_valid():
            profile = form.save(
                commit=False
            )
            profile.updated_by = request.user
            profile.save()

            messages.success(
                request,
                'Technique profile was updated.',
            )

            return redirect(
                'video_library:technique_profile_list'
            )

    else:
        form = TechniqueProfileForm(
            instance=profile,
        )

    return render(
        request,
        'video_library/technique_profile_form.html',
        {
            'form': form,
            'profile': profile,
        },
    )


# ============================================================
# ATHLETE SKILL PROGRESS
# ============================================================


@login_required
def athlete_skill_progress(
    request,
    athlete_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'view athlete skill progress.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )

    skill_name = (
        request.GET.get(
            'skill',
            '',
        )
        .strip()
    )

    if not skill_name:

        messages.error(
            request,
            'Choose a skill to view progress.',
        )

        return redirect(
            'video_library:athlete_video_timeline',
            athlete_id=athlete.id,
        )


    # ============================================================
    # VIDEOS
    # ============================================================

    videos = (
        get_accessible_videos(
            request.user
        )
        .filter(
            primary_athlete=athlete,
            skill_name__iexact=skill_name,
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
        .prefetch_related(
            'analyses__moments',
        )
        .order_by(
            'recorded_at',
            'uploaded_at',
        )
    )


    reference_video = (
        videos
        .filter(
            is_reference_attempt=True,
        )
        .first()
    )


    # ============================================================
    # ATTEMPTS
    # ============================================================

    attempts = []

    trend_labels = []
    knee_trend = []
    hip_trend = []
    shoulder_trend = []
    elbow_trend = []


    for video in videos:

        analysis = (
            video.analyses
            .filter(
                status=(
                    VideoAnalysis.STATUS_COMPLETED
                ),
            )
            .order_by(
                '-created_at',
            )
            .first()
        )

        peak_data = None


        if analysis:

            peak_candidates = []


            for moment in (
                analysis.moments.all()
            ):

                measurements = (
                    moment.measurements
                    or {}
                )

                if (
                    measurements.get(
                        'skill_phase'
                    )
                    != 'peak'
                ):
                    continue

                peak_candidates.append(
                    moment
                )


            if peak_candidates:

                key_candidates = [
                    moment
                    for moment
                    in peak_candidates
                    if (
                        moment.measurements
                        or {}
                    ).get(
                        'is_key_frame'
                    )
                ]

                available = (
                    key_candidates
                    or peak_candidates
                )


                best_peak = max(
                    available,
                    key=lambda moment: float(
                        (
                            moment.measurements
                            or {}
                        ).get(
                            'frame_quality_score'
                        )
                        or 0.0
                    ),
                )


                measurements = (
                    best_peak.measurements
                    or {}
                )

                gymnastics = (
                    measurements.get(
                        'gymnastics_measurements'
                    )
                    or {}
                )


                def get_angle(
                    section,
                ):
                    data = (
                        gymnastics.get(
                            section
                        )
                        or {}
                    )

                    value = (
                        data.get(
                            'average_angle'
                        )
                    )

                    try:

                        if value is None:
                            return None

                        return round(
                            float(value),
                            1,
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        return None


                peak_data = {

                    'timestamp': (
                        best_peak.timestamp_seconds
                    ),

                    'moment_id': (
                        best_peak.id
                    ),

                    'frame_image': (
                        best_peak.frame_image
                    ),

                    'frame_number': (
                        measurements.get(
                            'frame_number'
                        )
                    ),

                    'frame_score': (
                        measurements.get(
                            'frame_quality_score'
                        )
                    ),

                    'knee_angle': (
                        get_angle(
                            'knee_extension'
                        )
                    ),

                    'hip_angle': (
                        get_angle(
                            'hip_position'
                        )
                    ),

                    'shoulder_angle': (
                        get_angle(
                            'shoulder_position'
                        )
                    ),

                    'elbow_angle': (
                        get_angle(
                            'elbow_extension'
                        )
                    ),
                }


        attempt_date = (
            video.recorded_at
            or video.uploaded_at
        )


        attempts.append({

            'video': video,

            'analysis': analysis,

            'peak': peak_data,

            'attempt_date': (
                attempt_date
            ),
        })


        if (
            analysis
            and peak_data
        ):

            trend_labels.append(
                attempt_date.strftime(
                    '%b %d'
                )
            )

            knee_trend.append(
                peak_data[
                    'knee_angle'
                ]
            )

            hip_trend.append(
                peak_data[
                    'hip_angle'
                ]
            )

            shoulder_trend.append(
                peak_data[
                    'shoulder_angle'
                ]
            )

            elbow_trend.append(
                peak_data[
                    'elbow_angle'
                ]
            )


    # ============================================================
    # ANALYZED ATTEMPTS
    # ============================================================

    analyzed_attempts = [
        attempt
        for attempt
        in attempts
        if (
            attempt[
                'analysis'
            ]
            and
            attempt[
                'peak'
            ]
        )
    ]


    latest_attempt = (
        analyzed_attempts[-1]
        if analyzed_attempts
        else None
    )


    previous_attempt = (
        analyzed_attempts[-2]
        if len(
            analyzed_attempts
        ) >= 2
        else None
    )


    # ============================================================
    # TREND DATA
    # ============================================================

    trend_data = {

        'labels': (
            trend_labels
        ),

        'knee': (
            knee_trend
        ),

        'hip': (
            hip_trend
        ),

        'shoulder': (
            shoulder_trend
        ),

        'elbow': (
            elbow_trend
        ),
    }


    # ============================================================
    # CONSISTENCY TRACKING
    # ============================================================

    def build_consistency_metric(
        label,
        values,
    ):

        clean_values = [
            float(value)
            for value
            in values
            if value is not None
        ]


        if len(
            clean_values
        ) < 2:

            return {

                'label': label,

                'status': (
                    'Not Enough Data'
                ),

                'score': None,

                'standard_deviation': (
                    None
                ),

                'attempt_count': len(
                    clean_values
                ),
            }


        standard_deviation = (
            statistics.pstdev(
                clean_values
            )
        )


        score = max(
            0,
            min(
                100,
                round(
                    100
                    - (
                        standard_deviation
                        * 4
                    )
                ),
            ),
        )


        if (
            standard_deviation
            <= 2.5
        ):

            status = (
                'Very Consistent'
            )

        elif (
            standard_deviation
            <= 5.0
        ):

            status = (
                'Consistent'
            )

        elif (
            standard_deviation
            <= 8.0
        ):

            status = (
                'Variable'
            )

        else:

            status = (
                'Highly Variable'
            )


        return {

            'label': label,

            'status': status,

            'score': score,

            'standard_deviation': round(
                standard_deviation,
                1,
            ),

            'attempt_count': len(
                clean_values
            ),
        }


    consistency_metrics = [

        build_consistency_metric(
            'Knee Position',
            knee_trend,
        ),

        build_consistency_metric(
            'Hip Position',
            hip_trend,
        ),

        build_consistency_metric(
            'Shoulder Position',
            shoulder_trend,
        ),

        build_consistency_metric(
            'Elbow Position',
            elbow_trend,
        ),
    ]


    scored_metrics = [
        metric
        for metric
        in consistency_metrics
        if metric[
            'score'
        ] is not None
    ]


    overall_consistency_score = (
        None
    )

    most_stable_metric = None
    most_variable_metric = None


    if scored_metrics:

        overall_consistency_score = round(
            sum(
                metric[
                    'score'
                ]
                for metric
                in scored_metrics
            )
            /
            len(
                scored_metrics
            )
        )


        most_stable_metric = max(
            scored_metrics,
            key=lambda metric: (
                metric[
                    'score'
                ]
            ),
        )


        most_variable_metric = min(
            scored_metrics,
            key=lambda metric: (
                metric[
                    'score'
                ]
            ),
        )


    # ============================================================
    # VISUAL PROGRESS STORY
    # ============================================================

    progress_story = []


    for attempt in attempts:

        video = (
            attempt[
                'video'
            ]
        )

        analysis = (
            attempt[
                'analysis'
            ]
        )

        peak = (
            attempt[
                'peak'
            ]
        )


        if (
            not analysis
            or not peak
        ):
            continue


        progress_story.append({

            'video': video,

            'analysis': analysis,

            'peak': peak,

            'date': (
                video.recorded_at
                or video.uploaded_at
            ),

            'is_latest': bool(
                latest_attempt
                and
                video.id
                ==
                latest_attempt[
                    'video'
                ].id
            ),

            'is_reference': bool(
                reference_video
                and
                video.id
                ==
                reference_video.id
            ),

            'is_personal_best': (
                video.is_personal_best
            ),

            'is_coaching_example': (
                video.is_coaching_example
            ),
        })


    first_story_attempt = (
        progress_story[0]
        if progress_story
        else None
    )


    latest_story_attempt = (
        progress_story[-1]
        if progress_story
        else None
    )


    # ============================================================
    # COACH-FACING PROGRESS SUMMARY
    # ============================================================

    progress_summary = {

        'has_enough_data': False,

        'headline': '',

        'statements': [],

        'largest_change': None,

        'most_stable': None,

        'reference_match': None,
    }


    if len(
        analyzed_attempts
    ) >= 2:

        first_attempt = (
            analyzed_attempts[0]
        )

        latest_attempt_for_summary = (
            analyzed_attempts[-1]
        )

        first_peak = (
            first_attempt[
                'peak'
            ]
        )

        latest_peak = (
            latest_attempt_for_summary[
                'peak'
            ]
        )


        measurement_definitions = [

            (
                'knee_angle',
                'Knee Position',
            ),

            (
                'hip_angle',
                'Hip Position',
            ),

            (
                'shoulder_angle',
                'Shoulder Position',
            ),

            (
                'elbow_angle',
                'Elbow Position',
            ),
        ]


        measurement_changes = []


        for (
            key,
            label,
        ) in measurement_definitions:

            first_value = (
                first_peak.get(
                    key
                )
            )

            latest_value = (
                latest_peak.get(
                    key
                )
            )


            if (
                first_value is None
                or latest_value is None
            ):
                continue


            difference = (
                float(
                    latest_value
                )
                -
                float(
                    first_value
                )
            )


            measurement_changes.append({

                'key': key,

                'label': label,

                'first_value': round(
                    float(
                        first_value
                    ),
                    1,
                ),

                'latest_value': round(
                    float(
                        latest_value
                    ),
                    1,
                ),

                'difference': round(
                    difference,
                    1,
                ),

                'absolute_change': round(
                    abs(
                        difference
                    ),
                    1,
                ),
            })


        if measurement_changes:

            largest_change = max(
                measurement_changes,
                key=lambda item: (
                    item[
                        'absolute_change'
                    ]
                ),
            )


            most_stable_change = min(
                measurement_changes,
                key=lambda item: (
                    item[
                        'absolute_change'
                    ]
                ),
            )


            progress_summary[
                'largest_change'
            ] = (
                largest_change
            )


            progress_summary[
                'most_stable'
            ] = (
                most_stable_change
            )


            progress_summary[
                'statements'
            ].append(
                (
                    f'{largest_change["label"]} '
                    f'has changed the most from the '
                    f'first analyzed attempt to the latest '
                    f'({largest_change["absolute_change"]}°).'
                )
            )


            progress_summary[
                'statements'
            ].append(
                (
                    f'{most_stable_change["label"]} '
                    f'has remained the most similar '
                    f'from the first analyzed attempt '
                    f'to the latest '
                    f'({most_stable_change["absolute_change"]}° change).'
                )
            )


        # --------------------------------------------------------
        # CONSISTENCY SUMMARY
        # --------------------------------------------------------

        if (
            overall_consistency_score
            is not None
        ):

            if (
                overall_consistency_score
                >= 90
            ):

                consistency_text = (
                    'Peak positions are currently '
                    'very repeatable across attempts.'
                )

            elif (
                overall_consistency_score
                >= 80
            ):

                consistency_text = (
                    'Peak positions are showing '
                    'good repeatability.'
                )

            elif (
                overall_consistency_score
                >= 65
            ):

                consistency_text = (
                    'Peak positions are moderately '
                    'consistent but still vary '
                    'between attempts.'
                )

            else:

                consistency_text = (
                    'Peak positions currently show '
                    'meaningful variation between attempts.'
                )


            progress_summary[
                'statements'
            ].append(
                consistency_text
            )


        # --------------------------------------------------------
        # LATEST VS REFERENCE
        # --------------------------------------------------------

        reference_attempt = None


        if reference_video:

            for attempt in (
                analyzed_attempts
            ):

                if (
                    attempt[
                        'video'
                    ].id
                    ==
                    reference_video.id
                ):

                    reference_attempt = (
                        attempt
                    )

                    break


        if (
            reference_attempt
            and
            latest_attempt_for_summary[
                'video'
            ].id
            != reference_video.id
        ):

            reference_peak = (
                reference_attempt[
                    'peak'
                ]
            )


            reference_differences = []


            for (
                key,
                label,
            ) in measurement_definitions:

                latest_value = (
                    latest_peak.get(
                        key
                    )
                )

                reference_value = (
                    reference_peak.get(
                        key
                    )
                )


                if (
                    latest_value is None
                    or reference_value is None
                ):
                    continue


                difference = abs(
                    float(
                        latest_value
                    )
                    -
                    float(
                        reference_value
                    )
                )


                reference_differences.append({

                    'key': key,

                    'label': label,

                    'difference': round(
                        difference,
                        1,
                    ),
                })


            if reference_differences:

                closest_reference_metric = min(
                    reference_differences,
                    key=lambda item: (
                        item[
                            'difference'
                        ]
                    ),
                )


                furthest_reference_metric = max(
                    reference_differences,
                    key=lambda item: (
                        item[
                            'difference'
                        ]
                    ),
                )


                average_reference_difference = round(
                    sum(
                        item[
                            'difference'
                        ]
                        for item
                        in reference_differences
                    )
                    /
                    len(
                        reference_differences
                    ),
                    1,
                )


                progress_summary[
                    'reference_match'
                ] = {

                    'average_difference': (
                        average_reference_difference
                    ),

                    'closest': (
                        closest_reference_metric
                    ),

                    'furthest': (
                        furthest_reference_metric
                    ),
                }


                progress_summary[
                    'statements'
                ].append(
                    (
                        f'The latest attempt averages '
                        f'{average_reference_difference}° '
                        f'away from the current reference '
                        f'across available Peak measurements.'
                    )
                )


                progress_summary[
                    'statements'
                ].append(
                    (
                        f'{closest_reference_metric["label"]} '
                        f'is currently the closest measurement '
                        f'to the reference '
                        f'({closest_reference_metric["difference"]}° difference).'
                    )
                )


                progress_summary[
                    'statements'
                ].append(
                    (
                        f'{furthest_reference_metric["label"]} '
                        f'currently differs the most '
                        f'from the reference '
                        f'({furthest_reference_metric["difference"]}° difference).'
                    )
                )


        progress_summary[
            'has_enough_data'
        ] = True


        progress_summary[
            'headline'
        ] = (
            f'{skill_name} Progress Snapshot'
        )


    # ============================================================
    # COACHING GOALS
    # ============================================================

    active_goals = (
        SkillGoal.objects
        .filter(
            athlete=athlete,
            skill_name__iexact=skill_name,
            status=(
                SkillGoal.STATUS_ACTIVE
            ),
        )
        .select_related(
            'reference_video',
            'created_by',
        )
        .order_by(
            '-created_at',
        )
    )


    paused_goals = (
        SkillGoal.objects
        .filter(
            athlete=athlete,
            skill_name__iexact=skill_name,
            status=(
                SkillGoal.STATUS_PAUSED
            ),
        )
        .select_related(
            'reference_video',
            'created_by',
        )
        .order_by(
            '-updated_at',
        )
    )


    completed_goals = (
        SkillGoal.objects
        .filter(
            athlete=athlete,
            skill_name__iexact=skill_name,
            status=(
                SkillGoal.STATUS_COMPLETED
            ),
        )
        .select_related(
            'reference_video',
            'created_by',
        )
        .order_by(
            '-completed_at',
        )
    )


    # ============================================================
    # CONTEXT
    # ============================================================

    context = {

        'athlete': athlete,

        'skill_name': (
            skill_name
        ),

        'attempts': (
            attempts
        ),

        'attempt_count': len(
            attempts
        ),

        'analyzed_attempt_count': len(
            analyzed_attempts
        ),

        'latest_attempt': (
            latest_attempt
        ),

        'previous_attempt': (
            previous_attempt
        ),

        'reference_video': (
            reference_video
        ),

        'trend_data': (
            trend_data
        ),

        'consistency_metrics': (
            consistency_metrics
        ),

        'overall_consistency_score': (
            overall_consistency_score
        ),

        'most_stable_metric': (
            most_stable_metric
        ),

        'most_variable_metric': (
            most_variable_metric
        ),

        'progress_story': (
            progress_story
        ),

        'progress_story_count': len(
            progress_story
        ),

        'first_story_attempt': (
            first_story_attempt
        ),

        'latest_story_attempt': (
            latest_story_attempt
        ),

        'progress_summary': (
            progress_summary
        ),

        'active_goals': (
            active_goals
        ),

        'paused_goals': (
            paused_goals
        ),

        'completed_goals': (
            completed_goals
        ),
    }


    return render(
        request,
        'video_library/athlete_skill_progress.html',
        context,
    )


# ============================================================
# CREATE SKILL GOAL
# ============================================================


@login_required
@require_POST
def create_skill_goal(
    request,
    athlete_id,
):
    if not user_is_coach(
        request.user
    ):

        messages.error(
            request,
            'Only coaches can create skill goals.',
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    skill_name = (
        request.POST.get(
            'skill_name',
            '',
        )
        .strip()
    )


    title = (
        request.POST.get(
            'title',
            '',
        )
        .strip()
    )


    description = (
        request.POST.get(
            'description',
            '',
        )
        .strip()
    )


    use_reference = (
        request.POST.get(
            'use_reference'
        )
        == 'yes'
    )


    if not skill_name:

        messages.error(
            request,
            'A skill name is required.',
        )

        return redirect(
            'video_library:athlete_video_timeline',
            athlete_id=athlete.id,
        )


    progress_url = reverse(
        'video_library:athlete_skill_progress',
        kwargs={
            'athlete_id': athlete.id,
        },
    )


    if not title:

        messages.error(
            request,
            'Enter a coaching goal.',
        )

        return redirect(
            f'{progress_url}?skill={skill_name}'
        )


    reference_video = None


    if use_reference:

        reference_video = (
            get_accessible_videos(
                request.user
            )
            .filter(
                primary_athlete=athlete,
                skill_name__iexact=(
                    skill_name
                ),
                is_reference_attempt=True,
            )
            .first()
        )


    SkillGoal.objects.create(

        athlete=athlete,

        skill_name=(
            skill_name
        ),

        title=(
            title
        ),

        description=(
            description
        ),

        reference_video=(
            reference_video
        ),

        created_by=(
            request.user
        ),
    )


    messages.success(
        request,
        'Coaching goal was created.',
    )


    return redirect(
        f'{progress_url}?skill={skill_name}'
    )


# ============================================================
# UPDATE SKILL GOAL STATUS
# ============================================================


@login_required
@require_POST
def update_skill_goal_status(
    request,
    goal_id,
):
    if not user_is_coach(
        request.user
    ):

        messages.error(
            request,
            'Only coaches can update skill goals.',
        )

        return redirect(
            'role_redirect'
        )


    goal = get_object_or_404(
        SkillGoal.objects.select_related(
            'athlete',
        ),
        id=goal_id,
    )


    action = (
        request.POST.get(
            'action',
            '',
        )
        .strip()
        .lower()
    )


    progress_url = reverse(
        'video_library:athlete_skill_progress',
        kwargs={
            'athlete_id': (
                goal.athlete_id
            ),
        },
    )


    allowed_actions = {
        'complete',
        'pause',
        'reactivate',
    }


    if action not in allowed_actions:

        messages.error(
            request,
            'Choose a valid goal action.',
        )

        return redirect(
            (
                f'{progress_url}'
                f'?skill={goal.skill_name}'
            )
        )


    if action == 'complete':

        goal.status = (
            SkillGoal.STATUS_COMPLETED
        )

        goal.completed_at = (
            timezone.now()
        )

        message = (
            'Coaching goal was marked completed.'
        )


    elif action == 'pause':

        goal.status = (
            SkillGoal.STATUS_PAUSED
        )

        goal.completed_at = None

        message = (
            'Coaching goal was paused.'
        )


    else:

        goal.status = (
            SkillGoal.STATUS_ACTIVE
        )

        goal.completed_at = None

        message = (
            'Coaching goal was reactivated.'
        )


    goal.save(
        update_fields=[
            'status',
            'completed_at',
            'updated_at',
        ],
    )


    messages.success(
        request,
        message,
    )


    return redirect(
        (
            f'{progress_url}'
            f'?skill={goal.skill_name}'
        )
    )
