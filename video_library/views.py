
from pathlib import Path
from .ai import VideoAnalysisProcessor
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST
User = get_user_model()
from .models import (
    Video,
    VideoAnalysis,
    VideoAnalysisFeedback,
    VideoAnalysisMoment,
)

COACH_ROLES = [
    'coach',
    'head_coach',
]


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

    return videos.filter(
        Q(uploaded_by=user)
        | Q(training_group__coaches=user)
        | Q(training_group__isnull=True)
    ).distinct()


@login_required
def video_dashboard(request):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    accessible_videos = get_accessible_videos(
        request.user
    )

    recent_videos = (
        accessible_videos
        .filter(
            status=Video.STATUS_READY,
        )
        .order_by(
            '-uploaded_at',
        )[:12]
    )

    context = {
        'recent_videos': recent_videos,
        'total_video_count': (
            accessible_videos.exclude(
                status=Video.STATUS_ARCHIVED,
            ).count()
        ),
        'favorite_count': (
            accessible_videos.filter(
                is_favorite=True,
                status=Video.STATUS_READY,
            ).count()
        ),
        'pending_ai_count': (
            accessible_videos.filter(
                ai_status__in=[
                    Video.AI_QUEUED,
                    Video.AI_PROCESSING,
                ],
            ).count()
        ),
    }

    return render(
        request,
        'video_library/dashboard.html',
        context,
    )


@login_required
def video_list(request):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    videos = (
        get_accessible_videos(
            request.user
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
    )

    search_query = request.GET.get(
        'search',
        '',
    ).strip()

    athlete_filter = request.GET.get(
        'athlete',
        '',
    ).strip()

    event_filter = request.GET.get(
        'event',
        '',
    ).strip()

    type_filter = request.GET.get(
        'video_type',
        '',
    ).strip()

    favorite_filter = request.GET.get(
        'favorites',
        '',
    ).strip()

    date_from = request.GET.get(
        'date_from',
        '',
    ).strip()

    date_to = request.GET.get(
        'date_to',
        '',
    ).strip()

    if search_query:
        videos = videos.filter(
            Q(
                title__icontains=search_query
            )
            | Q(
                skill_name__icontains=search_query
            )
            | Q(
                tags__icontains=search_query
            )
            | Q(
                notes__icontains=search_query
            )
            | Q(
                primary_athlete__username__icontains=(
                    search_query
                )
            )
            | Q(
                primary_athlete__first_name__icontains=(
                    search_query
                )
            )
            | Q(
                primary_athlete__last_name__icontains=(
                    search_query
                )
            )
            | Q(
                tagged_athletes__username__icontains=(
                    search_query
                )
            )
            | Q(
                tagged_athletes__first_name__icontains=(
                    search_query
                )
            )
            | Q(
                tagged_athletes__last_name__icontains=(
                    search_query
                )
            )
        ).distinct()

    if athlete_filter:
        videos = videos.filter(
            Q(
                primary_athlete_id=athlete_filter
            )
            | Q(
                tagged_athletes__id=athlete_filter
            )
        ).distinct()

    if event_filter:
        videos = videos.filter(
            event=event_filter,
        )

    if type_filter:
        videos = videos.filter(
            video_type=type_filter,
        )

    if favorite_filter == 'yes':
        videos = videos.filter(
            is_favorite=True,
        )

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
        User.objects.filter(
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
        'video_type_choices': (
            Video.VIDEO_TYPE_CHOICES
        ),
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


@login_required
def video_detail(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'access the Video Library.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    video = get_object_or_404(
        get_accessible_videos(
            request.user
        ).prefetch_related(
            'reviews__assigned_coach',
        ),
        id=video_id,
    )

    related_videos = (
        get_accessible_videos(
            request.user
        )
        .exclude(
            id=video.id,
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
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
        .order_by(
            '-created_at',
        )
        .first()
    )

    analysis_moment_items = []

    if latest_analysis:
        coach_feedback = {
            feedback.moment_id: feedback
            for feedback in (
                latest_analysis.feedback_entries
                .filter(
                    coach=request.user,
                    moment__isnull=False,
                )
                .select_related(
                    'moment',
                )
            )
        }

        analysis_moment_items = [
            {
                'moment': moment,
                'feedback': coach_feedback.get(
                    moment.id
                ),
            }
            for moment in latest_analysis.moments.all()
        ]
    analysis_count = (
        video.analyses.count()
    )
    context = {
        'video': video,
        'related_videos': related_videos,
        'latest_analysis': latest_analysis,
        'analysis_moment_items': analysis_moment_items,
        'analysis_count': analysis_count,
    }



    return render(
        request,
        'video_library/video_detail.html',
        context,
    )

@login_required
@require_POST
def review_video_analysis(
    request,
    analysis_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this analysis.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects
        .select_related(
            'video',
        ),
        id=analysis_id,
    )

    can_access = (
        get_accessible_videos(
            request.user
        )
        .filter(
            id=analysis.video_id,
        )
        .exists()
    )

    if not can_access:
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

    review_status = request.POST.get(
        'review_status',
        '',
    ).strip()

    review_notes = request.POST.get(
        'coach_review_notes',
        '',
    ).strip()

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
        (
            'Your analysis review was saved.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=analysis.video_id,
    )
@login_required
@require_POST
def review_analysis_moment(
    request,
    moment_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'review this observation.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    moment = get_object_or_404(
        VideoAnalysisMoment.objects
        .select_related(
            'analysis__video',
        ),
        id=moment_id,
    )

    analysis = moment.analysis

    can_access = (
        get_accessible_videos(
            request.user
        )
        .filter(
            id=analysis.video_id,
        )
        .exists()
    )

    if not can_access:
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
                'Only completed analyses can '
                'receive feedback.'
            ),
        )

        return redirect(
            'video_library:video_detail',
            video_id=analysis.video_id,
        )

    rating = request.POST.get(
        'rating',
        '',
    ).strip()

    comment = request.POST.get(
        'comment',
        '',
    ).strip()

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
            f'was saved.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=analysis.video_id,
    )

@login_required
@require_POST
def request_video_analysis(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'analyze this video.'
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

    active_analysis = (
        video.analyses
        .filter(
            status__in=[
                VideoAnalysis.STATUS_QUEUED,
                VideoAnalysis.STATUS_PREPARING,
                VideoAnalysis.STATUS_PROCESSING,
                (
                    VideoAnalysis
                    .STATUS_GENERATING_RESULTS
                ),
            ],
        )
        .order_by(
            '-created_at',
        )
        .first()
    )

    if active_analysis:
        messages.info(
            request,
            (
                'This video already has an analysis '
                'in progress.'
            ),
        )

        return redirect(
            'video_library:video_detail',
            video_id=video.id,
        )

    analysis = VideoAnalysis.objects.create(
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
        (
            'Video analysis was added to the queue.'
        ),
    )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


@login_required
def video_analysis_status(
    request,
    analysis_id,
):
    if not user_is_coach(
        request.user
    ):
        return JsonResponse(
            {
                'error': 'Permission denied.',
            },
            status=403,
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects
        .select_related(
            'video',
        ),
        id=analysis_id,
    )

    accessible_video = (
        get_accessible_videos(
            request.user
        )
        .filter(
            id=analysis.video_id,
        )
        .exists()
    )

    if not accessible_video:
        return JsonResponse(
            {
                'error': 'Permission denied.',
            },
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


@login_required
def video_analysis_history(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'view analysis history.'
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
        .order_by(
            '-created_at',
        )
    )

    active_analysis = analyses.filter(
        status__in=[
            VideoAnalysis.STATUS_QUEUED,
            VideoAnalysis.STATUS_PREPARING,
            VideoAnalysis.STATUS_PROCESSING,
            (
                VideoAnalysis
                .STATUS_GENERATING_RESULTS
            ),
        ],
    ).first()

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
@login_required
def video_analysis_detail(
    request,
    analysis_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'view this analysis.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects
        .select_related(
            'video',
            'requested_by',
            'reviewed_by',
        )
        .prefetch_related(
            'moments',
            'feedback_entries',
        ),
        id=analysis_id,
    )

    can_access = (
        get_accessible_videos(
            request.user
        )
        .filter(
            id=analysis.video_id,
        )
        .exists()
    )

    if not can_access:
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
            analysis.feedback_entries
            .filter(
                coach=request.user,
                moment__isnull=False,
            )
            .select_related(
                'moment',
            )
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
        .order_by(
            '-created_at',
        )
        .first()
    )

    next_analysis = (
        analysis.video.analyses
        .filter(
            created_at__gt=analysis.created_at,
        )
        .order_by(
            'created_at',
        )
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
    }

    return render(
        request,
        'video_library/analysis_detail.html',
        context,
    )
@login_required
@require_POST
def rerun_video_analysis(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'analyze this video.'
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

    active_analysis = (
        video.analyses
        .filter(
            status__in=[
                VideoAnalysis.STATUS_QUEUED,
                VideoAnalysis.STATUS_PREPARING,
                VideoAnalysis.STATUS_PROCESSING,
                (
                    VideoAnalysis
                    .STATUS_GENERATING_RESULTS
                ),
            ],
        )
        .order_by(
            '-created_at',
        )
        .first()
    )

    if active_analysis:
        messages.info(
            request,
            (
                'This video already has an analysis '
                'in progress.'
            ),
        )

        return redirect(
            'video_library:analysis_detail',
            analysis_id=active_analysis.id,
        )

    latest_analysis = (
        video.analyses
        .order_by(
            '-created_at',
        )
        .first()
    )

    requested_skill = (
        video.skill_name.strip()
    )

    if (
        not requested_skill
        and latest_analysis
    ):
        requested_skill = (
            latest_analysis.requested_skill
            or latest_analysis.detected_skill
        )

    analysis = VideoAnalysis.objects.create(
        video=video,
        requested_by=request.user,
        status=VideoAnalysis.STATUS_QUEUED,
        progress_percentage=0,
        current_step='Waiting to begin',
        analysis_source=(
            VideoAnalysis.SOURCE_MOCK
        ),
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


@login_required
@require_POST
@login_required
@require_POST
def process_mock_analysis(
    request,
    analysis_id,
):
    if not user_is_coach(
        request.user
    ):
        return JsonResponse(
            {
                'error': 'Permission denied.',
            },
            status=403,
        )

    analysis = get_object_or_404(
        VideoAnalysis.objects
        .select_related(
            'video',
        ),
        id=analysis_id,
    )

    accessible_video = (
        get_accessible_videos(
            request.user
        )
        .filter(
            id=analysis.video_id,
        )
        .exists()
    )

    if not accessible_video:
        return JsonResponse(
            {
                'error': 'Permission denied.',
            },
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

        processor.process(
            analysis=analysis,
        )

    except Exception as error:
        return JsonResponse(
            {
                'status': analysis.status,
                'status_display': (
                    analysis.get_status_display()
                ),
                'progress_percentage': (
                    analysis.progress_percentage
                ),
                'current_step': analysis.current_step,
                'is_finished': True,
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
@login_required
def athlete_video_compare_select(
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
                'compare athlete videos.'
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

    videos = (
        get_accessible_videos(
            request.user
        )
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
        .distinct()
        .order_by(
            '-recorded_at',
            '-uploaded_at',
        )
    )

    event_filter = request.GET.get(
        'event',
        '',
    ).strip()

    skill_filter = request.GET.get(
        'skill',
        '',
    ).strip()

    if event_filter:
        videos = videos.filter(
            event=event_filter,
        )

    if skill_filter:
        videos = videos.filter(
            skill_name__iexact=skill_filter,
        )

    skill_names = (
        get_accessible_videos(
            request.user
        )
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(
            skill_name='',
        )
        .values_list(
            'skill_name',
            flat=True,
        )
        .distinct()
        .order_by(
            'skill_name',
        )
    )

    context = {
        'athlete': athlete,
        'videos': videos,
        'event_choices': Video.EVENT_CHOICES,
        'event_filter': event_filter,
        'skill_filter': skill_filter,
        'skill_names': skill_names,
        'result_count': videos.count(),
    }

    return render(
        request,
        'video_library/compare_select.html',
        context,
    )

@login_required
def video_compare(
    request,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'compare videos.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    first_video_id = request.GET.get(
        'video_1',
        '',
    ).strip()

    second_video_id = request.GET.get(
        'video_2',
        '',
    ).strip()

    if not first_video_id or not second_video_id:
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

    context = {
        'first_video': first_video,
        'second_video': second_video,
        'shared_athlete': shared_athlete,
    }

    return render(
        request,
        'video_library/video_compare.html',
        context,
    )

@login_required
def athlete_video_timeline(
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
                'access athlete video timelines.'
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

    videos = (
        get_accessible_videos(
            request.user
        )
        .filter(
            Q(primary_athlete=athlete)
            | Q(tagged_athletes=athlete)
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
        .distinct()
        .order_by(
            '-recorded_at',
            '-uploaded_at',
        )
    )

    event_sections = []

    for event_value, event_label in Video.EVENT_CHOICES:
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
        if video.skill_name.strip()
    })

    context = {
        'athlete': athlete,
        'videos': videos,
        'event_sections': event_sections,
        'total_video_count': videos.count(),
        'favorite_count': videos.filter(
            is_favorite=True,
        ).count(),
        'event_count': len(
            event_sections
        ),
        'skill_count': len(
            skill_names
        ),
        'skill_names': skill_names,
    }

    return render(
        request,
        'video_library/athlete_timeline.html',
        context,
    )

@login_required
@require_POST
def toggle_video_favorite(
    request,
    video_id,
):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'You do not have permission to '
                'update this video.'
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

    video.is_favorite = (
        not video.is_favorite
    )

    video.save(
        update_fields=[
            'is_favorite',
            'updated_at',
        ],
    )

    if video.is_favorite:
        messages.success(
            request,
            (
                f'"{video.title}" was added '
                f'to favorites.'
            ),
        )
    else:
        messages.success(
            request,
            (
                f'"{video.title}" was removed '
                f'from favorites.'
            ),
        )

    next_url = request.POST.get(
        'next'
    )

    if next_url:
        return redirect(
            next_url
        )

    return redirect(
        'video_library:video_detail',
        video_id=video.id,
    )


@login_required
def video_upload(request):
    if not user_is_coach(
        request.user
    ):
        messages.error(
            request,
            (
                'Only coaches and head coaches can '
                'upload videos.'
            ),
        )

        return redirect(
            'role_redirect'
        )

    if request.method == 'POST':
        form = VideoUploadForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            uploaded_files = (
                form.cleaned_data[
                    'videos'
                ]
            )

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
                        ].strip()
                    )

                    if title_prefix:
                        if len(
                            uploaded_files
                        ) > 1:
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

                    if form.cleaned_data[
                        'recorded_date'
                    ]:
                        recorded_at = (
                            timezone.make_aware(
                                timezone.datetime.combine(
                                    form.cleaned_data[
                                        'recorded_date'
                                    ],
                                    timezone.datetime.min.time(),
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
                        status=Video.STATUS_READY,
                    )

                    video.tagged_athletes.set(
                        form.cleaned_data[
                            'tagged_athletes'
                        ]
                    )

                    uploaded_videos.append(
                        video
                    )

            video_count = len(
                uploaded_videos
            )

            messages.success(
                request,
                (
                    f'{video_count} '
                    f'video'
                    f'{"s" if video_count != 1 else ""} '
                    f'uploaded successfully.'
                ),
            )

            return redirect(
                'video_library:dashboard'
            )

    else:
        form = VideoUploadForm(
            user=request.user,
        )

    context = {
        'form': form,
    }

    return render(
        request,
        'video_library/upload.html',
        context,
    )
