from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from athletes.models import AttendanceRecord
from coaches.models import TeamEvent
from communications.dashboard import (
    get_dashboard_communication_data,
)
from gyms.models import GymMembership
from performance_testing.models import (
    AthleteTestingResult,
)
from surveys.models import DailySurvey
from video_library.models import Video

from .forms import ConnectAthleteForm
from .models import ParentAthleteLink


# ============================================================
# ACCESS HELPERS
# ============================================================


def parent_access_denied(request):
    messages.error(
        request,
        'Only parents can access this page.',
    )

    return redirect('role_redirect')


def get_parent_links(user):
    """
    Return approved athlete connections belonging
    to the logged-in parent.
    """

    return (
        ParentAthleteLink.objects
        .filter(
            parent=user,
            approved=True,
        )
        .select_related('athlete')
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )


def get_parent_linked_athlete_ids(user):
    """
    Return IDs for athletes with approved parent links.
    """

    return (
        ParentAthleteLink.objects
        .filter(
            parent=user,
            approved=True,
        )
        .values_list(
            'athlete_id',
            flat=True,
        )
    )


def get_parent_gym_ids(user):
    """
    Return gyms belonging to the parent's approved
    linked athletes.
    """

    linked_athlete_ids = (
        get_parent_linked_athlete_ids(user)
    )

    return (
        GymMembership.objects
        .filter(
            user_id__in=linked_athlete_ids,
            role='athlete',
            is_active=True,
        )
        .values_list(
            'gym_id',
            flat=True,
        )
        .distinct()
    )


# ============================================================
# PARENT VIDEO ACCESS
# ============================================================


def get_parent_videos(
    user,
    athlete=None,
):
    """
    Return videos the logged-in parent can view.

    A video must:

    1. Be visible to parents.
    2. Include an approved linked athlete.
    3. Not be archived.
    """

    linked_athlete_ids = (
        get_parent_linked_athlete_ids(user)
    )

    videos = (
        Video.objects
        .filter(
            visibility=Video.VISIBILITY_PARENTS,
        )
        .filter(
            Q(
                primary_athlete_id__in=(
                    linked_athlete_ids
                )
            )
            |
            Q(
                tagged_athletes__id__in=(
                    linked_athlete_ids
                )
            )
        )
        .exclude(
            status=Video.STATUS_ARCHIVED,
        )
        .select_related(
            'primary_athlete',
            'training_group',
            'uploaded_by',
        )
        .prefetch_related(
            'tagged_athletes',
        )
        .distinct()
    )

    if athlete is not None:
        videos = (
            videos
            .filter(
                Q(
                    primary_athlete=athlete
                )
                |
                Q(
                    tagged_athletes=athlete
                )
            )
            .distinct()
        )

    return videos


# ============================================================
# PARENT READINESS STATUS
# ============================================================


def calculate_parent_readiness_status(
    survey,
):
    """
    Return a parent-friendly wellness summary.
    """

    if not survey:
        return {
            'label': 'Survey Not Completed',
            'level': 'unknown',
            'icon': '📝',
            'message': (
                'Today’s wellness survey has not '
                'been completed yet.'
            ),
        }

    low_sleep = (
        survey.sleep_hours is not None
        and survey.sleep_hours < 7
    )

    needs_attention = (
        survey.energy <= 2
        or survey.soreness >= 4
        or survey.stress >= 4
        or low_sleep
    )

    if needs_attention:
        return {
            'label': 'Coach Aware',
            'level': 'attention',
            'icon': '🟡',
            'message': (
                'Your child reported that they may '
                'need some extra support today. '
                'Their coach can review the details.'
            ),
        }

    return {
        'label': 'Ready to Train',
        'level': 'ready',
        'icon': '🟢',
        'message': (
            'Today’s wellness survey indicates that '
            'your child is ready for training.'
        ),
    }


# ============================================================
# PARENT DASHBOARD
# ============================================================


@login_required
def parent_dashboard(request):
    if request.user.role != 'parent':
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': request.user.role,
                'username': request.user.username,
            },
        )

    # --------------------------------------------------------
    # Linked athletes
    # --------------------------------------------------------

    links = get_parent_links(
        request.user
    )

    linked_athletes = [
        link.athlete
        for link in links
    ]

    selected_athlete = None

    selected_athlete_id = (
        request.GET.get('athlete')
    )

    if linked_athletes:
        if selected_athlete_id:
            selected_athlete = next(
                (
                    athlete
                    for athlete in linked_athletes
                    if (
                        str(athlete.id)
                        == selected_athlete_id
                    )
                ),
                None,
            )

            if selected_athlete is None:
                raise Http404(
                    'This athlete is not linked '
                    'to your account.'
                )

        else:
            selected_athlete = (
                linked_athletes[0]
            )

    context = {
        'linked_athletes': linked_athletes,
        'selected_athlete': selected_athlete,
        'dashboard_communication': (
            get_dashboard_communication_data(
                request.user
            )
        ),
    }

    if selected_athlete is None:
        return render(
            request,
            'parents_portal/dashboard.html',
            context,
        )

    today = timezone.now().date()

    # --------------------------------------------------------
    # Wellness
    # --------------------------------------------------------

    today_survey = (
        DailySurvey.objects
        .filter(
            athlete=selected_athlete,
            survey_date=today,
        )
        .first()
    )

    readiness_status = (
        calculate_parent_readiness_status(
            today_survey
        )
    )

    # --------------------------------------------------------
    # Attendance
    # --------------------------------------------------------

    attendance_records = (
        AttendanceRecord.objects
        .filter(
            athlete=selected_athlete,
        )
    )

    attendance_total = (
        attendance_records.count()
    )

    attendance_present = (
        attendance_records
        .filter(
            status='present',
        )
        .count()
    )

    attendance_late = (
        attendance_records
        .filter(
            status='late',
        )
        .count()
    )

    attendance_counted = (
        attendance_present
        + attendance_late
    )

    if attendance_total > 0:
        attendance_rate = round(
            (
                attendance_counted
                / attendance_total
            )
            * 100
        )

    else:
        attendance_rate = 0

    # --------------------------------------------------------
    # Performance testing
    # --------------------------------------------------------

    testing_queryset = (
        AthleteTestingResult.objects
        .filter(
            athlete=selected_athlete,
            status='verified',
            session__published_to_parents=True,
        )
        .select_related(
            'session',
            'verified_by',
        )
    )

    latest_testing_result = (
        testing_queryset
        .order_by(
            '-session__testing_date',
            '-session__created_at',
        )
        .first()
    )

    testing_results = list(
        testing_queryset
        .order_by(
            'session__testing_date',
            'session__created_at',
        )
    )

    testing_chart_labels = [
        result.session.testing_date.strftime(
            '%b %d'
        )
        for result in testing_results
    ]

    testing_chart_scores = [
        float(result.total_score)
        for result in testing_results
    ]

    testing_score_change = None
    testing_personal_best = None
    testing_trend = 'No trend yet'

    if testing_results:
        testing_personal_best = max(
            result.total_score
            for result in testing_results
        )

    if (
        latest_testing_result
        and len(testing_results) >= 2
    ):
        previous_result = (
            testing_results[-2]
        )

        testing_score_change = (
            latest_testing_result.total_score
            - previous_result.total_score
        )

        if testing_score_change > 0:
            testing_trend = 'Trending Up'

        elif testing_score_change < 0:
            testing_trend = (
                'Building Consistency'
            )

        else:
            testing_trend = (
                'Holding Steady'
            )

    # --------------------------------------------------------
    # Upcoming events
    # --------------------------------------------------------

    athlete_membership = (
        GymMembership.objects
        .filter(
            user=selected_athlete,
            role='athlete',
            is_active=True,
        )
        .select_related('gym')
        .first()
    )

    selected_gym = (
        athlete_membership.gym
        if athlete_membership
        else None
    )

    if selected_gym:
        upcoming_events = (
            TeamEvent.objects
            .filter(
                gym=selected_gym,
                event_date__gte=today,
            )
            .select_related(
                'gym',
                'created_by',
            )
            .order_by(
                'event_date',
                'start_time',
            )[:5]
        )

    else:
        upcoming_events = (
            TeamEvent.objects.none()
        )

    next_event = (
        upcoming_events.first()
    )

    days_until_next_event = None

    if next_event:
        days_until_next_event = (
            next_event.event_date
            - today
        ).days

    # --------------------------------------------------------
    # Parent video library
    # --------------------------------------------------------

    parent_videos = (
        get_parent_videos(
            request.user,
            athlete=selected_athlete,
        )
        .order_by(
            '-recorded_at',
            '-uploaded_at',
        )
    )

    parent_video_count = (
        parent_videos.count()
    )

    recent_parent_videos = list(
        parent_videos[:6]
    )

    # --------------------------------------------------------
    # Final context
    # --------------------------------------------------------

    context.update({
        'today': today,
        'today_survey': today_survey,
        'readiness_status': readiness_status,

        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_late': attendance_late,
        'attendance_rate': attendance_rate,

        'latest_testing_result': (
            latest_testing_result
        ),
        'testing_results': testing_results,
        'testing_score_change': (
            testing_score_change
        ),
        'testing_personal_best': (
            testing_personal_best
        ),
        'testing_trend': testing_trend,
        'testing_chart_labels': (
            testing_chart_labels
        ),
        'testing_chart_scores': (
            testing_chart_scores
        ),

        'upcoming_events': upcoming_events,
        'next_event': next_event,
        'days_until_next_event': (
            days_until_next_event
        ),

        'parent_videos': parent_videos,
        'recent_parent_videos': (
            recent_parent_videos
        ),
        'parent_video_count': (
            parent_video_count
        ),

        # Compatibility with the older dashboard template.
        'recent_videos': recent_parent_videos,
    })

    return render(
        request,
        'parents_portal/dashboard.html',
        context,
    )


# ============================================================
# PARENT EVENTS
# ============================================================


@login_required
def parent_events(request):
    if request.user.role != 'parent':
        return parent_access_denied(
            request
        )

    today = timezone.now().date()

    allowed_gym_ids = (
        get_parent_gym_ids(
            request.user
        )
    )

    events = (
        TeamEvent.objects
        .filter(
            gym_id__in=allowed_gym_ids,
        )
        .select_related(
            'gym',
            'created_by',
        )
    )

    upcoming_events = (
        events
        .filter(
            event_date__gte=today,
        )
        .order_by(
            'event_date',
            'start_time',
        )
    )

    past_events = (
        events
        .filter(
            event_date__lt=today,
        )
        .order_by(
            '-event_date',
            '-start_time',
        )[:10]
    )

    return render(
        request,
        'parents_portal/events.html',
        {
            'today': today,
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'upcoming_event_count': (
                upcoming_events.count()
            ),
        },
    )


# ============================================================
# PARENT VIDEO LIBRARY
# ============================================================


@login_required
def parent_video_library(request):
    if request.user.role != 'parent':
        return parent_access_denied(
            request
        )

    videos = (
        get_parent_videos(
            request.user
        )
        .order_by(
            '-recorded_at',
            '-uploaded_at',
        )
    )

    return render(
        request,
        'parents_portal/video_library.html',
        {
            'videos': videos,
            'video_count': videos.count(),
        },
    )


# ============================================================
# PARENT VIDEO DETAIL
# ============================================================


@login_required
def parent_video_detail(
    request,
    video_id,
):
    if request.user.role != 'parent':
        return parent_access_denied(
            request
        )

    video = get_object_or_404(
        get_parent_videos(
            request.user
        ),
        id=video_id,
    )

    return render(
        request,
        'parents_portal/video_detail.html',
        {
            'video': video,
        },
    )


# ============================================================
# CONNECT ATHLETE
# ============================================================


@login_required
def connect_athlete(request):
    if request.user.role != 'parent':
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': request.user.role,
                'username': request.user.username,
            },
        )

    parent_gym_ids = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='parent',
            is_active=True,
        )
        .values_list(
            'gym_id',
            flat=True,
        )
    )

    pending_links = (
        ParentAthleteLink.objects
        .filter(
            parent=request.user,
            approved=False,
        )
        .select_related('athlete')
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
        )
    )

    if request.method == 'POST':
        form = ConnectAthleteForm(
            request.POST
        )

        if form.is_valid():
            first_name = (
                form.cleaned_data[
                    'first_name'
                ].strip()
            )

            last_name = (
                form.cleaned_data[
                    'last_name'
                ].strip()
            )

            date_of_birth = (
                form.cleaned_data[
                    'date_of_birth'
                ]
            )

            relationship = (
                form.cleaned_data[
                    'relationship'
                ].strip()
            )

            athlete_membership = (
                GymMembership.objects
                .filter(
                    gym_id__in=parent_gym_ids,
                    role='athlete',
                    is_active=True,
                    user__first_name__iexact=first_name,
                    user__last_name__iexact=last_name,
                    user__athlete_profile__date_of_birth=date_of_birth,
                )
                .select_related(
                    'user',
                    'gym',
                    'user__athlete_profile',
                )
                .first()
            )

            if not athlete_membership:
                form.add_error(
                    None,
                    (
                        'We could not find an athlete '
                        'matching that name and date '
                        'of birth in your gym.'
                    ),
                )

            else:
                athlete = (
                    athlete_membership.user
                )

                existing_link = (
                    ParentAthleteLink.objects
                    .filter(
                        parent=request.user,
                        athlete=athlete,
                    )
                    .first()
                )

                if existing_link:
                    if existing_link.approved:
                        messages.info(
                            request,
                            (
                                'This athlete is already '
                                'connected to your account.'
                            ),
                        )

                    else:
                        messages.info(
                            request,
                            (
                                'Your connection request '
                                'is already waiting for '
                                'approval.'
                            ),
                        )

                    return redirect(
                        'connect_athlete'
                    )

                ParentAthleteLink.objects.create(
                    parent=request.user,
                    athlete=athlete,
                    relationship=relationship,
                    approved=False,
                )

                messages.success(
                    request,
                    (
                        'Connection request sent. A Gym '
                        'Director must approve it before '
                        'the athlete appears in your '
                        'account.'
                    ),
                )

                return redirect(
                    'connect_athlete'
                )

    else:
        form = ConnectAthleteForm()

    return render(
        request,
        'parents_portal/connect_athlete.html',
        {
            'form': form,
            'pending_links': pending_links,
        },
    )