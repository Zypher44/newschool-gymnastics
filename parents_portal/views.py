from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404

from django.utils import timezone

from athletes.models import AttendanceRecord
from coaches.models import TeamEvent
from communications.dashboard import (
    get_dashboard_communication_data,
)
from performance_testing.models import (
    AthleteTestingResult,
)
from surveys.models import DailySurvey
from video_library.models import Video

from .models import ParentAthleteLink
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.contrib import messages
from django.shortcuts import redirect

from athletes.models import AthleteProfile
from gyms.models import GymMembership

from .forms import ConnectAthleteForm

# ============================================================
# PARENT VIDEO ACCESS
# ============================================================


def get_parent_videos(
    user,
    athlete=None,
):
    """
    Return videos that the logged-in parent
    is allowed to view.

    A video is visible when:

    1. The video visibility is set to Parents.
    2. At least one linked athlete is either:
       - the primary athlete, or
       - a tagged athlete.

    If athlete is provided, only videos containing
    that specific linked athlete are returned.
    """

    linked_athlete_ids = (
        ParentAthleteLink.objects
        .filter(
            parent=user,
        )
        .values_list(
            'athlete_id',
            flat=True,
        )
    )


    videos = (
        Video.objects
        .filter(
            visibility=(
                Video.VISIBILITY_PARENTS
            ),
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
            status=(
                Video.STATUS_ARCHIVED
            ),
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
# PARENT VIDEO LIBRARY
# ============================================================


@login_required
def parent_video_library(
    request,
):
    if (
        request.user.role
        != 'parent'
    ):

        messages.error(
            request,
            (
                'Only parents can '
                'access this page.'
            ),
        )

        return redirect(
            'role_redirect'
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


    context = {

        'videos': (
            videos
        ),

        'video_count': (
            videos.count()
        ),
    }


    return render(
        request,
        'parents_portal/video_library.html',
        context,
    )


# ============================================================
# PARENT READINESS STATUS
# ============================================================


def calculate_parent_readiness_status(
    survey,
):
    """
    Return a parent-friendly wellness status.

    Parents receive a simple summary rather than
    detailed athlete wellness responses or
    internal coaching alerts.
    """

    if not survey:

        return {

            'label': (
                'Survey Not Completed'
            ),

            'level': (
                'unknown'
            ),

            'icon': (
                '📝'
            ),

            'message': (
                'Today’s wellness survey has '
                'not been completed yet.'
            ),
        }


    low_sleep = (
        survey.sleep_hours
        is not None
        and
        survey.sleep_hours < 7
    )


    needs_attention = (
        survey.energy <= 2
        or
        survey.soreness >= 4
        or
        survey.stress >= 4
        or
        low_sleep
    )


    if needs_attention:

        return {

            'label': (
                'Coach Aware'
            ),

            'level': (
                'attention'
            ),

            'icon': (
                '🟡'
            ),

            'message': (
                'Your child reported that they '
                'may need some extra support today. '
                'Their coach can review the details.'
            ),
        }


    return {

        'label': (
            'Ready to Train'
        ),

        'level': (
            'ready'
        ),

        'icon': (
            '🟢'
        ),

        'message': (
            'Today’s wellness survey indicates '
            'that your child is ready for training.'
        ),
    }


# ============================================================
# PARENT / ATHLETE LINKS
# ============================================================


def get_parent_links(user):
    return (
        ParentAthleteLink.objects
        .filter(
            parent=user,
            approved=True,
        )
        .select_related('athlete')
        .order_by(
            'athlete__first_name',
            'athlete__username'
        )
    )
# ============================================================
# PARENT DASHBOARD
# ============================================================


@login_required
def parent_dashboard(
    request,
):
    if (
        request.user.role
        != 'parent'
    ):

        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': (
                    request.user.role
                ),

                'username': (
                    request.user.username
                ),
            },
        )


    # ========================================================
    # LINKED ATHLETES
    # ========================================================

    links = (
        get_parent_links(
            request.user
        )
    )


    linked_athletes = [
        link.athlete
        for link
        in links
    ]


    selected_athlete = None


    selected_athlete_id = (
        request.GET.get(
            'athlete'
        )
    )


    if linked_athletes:

        if selected_athlete_id:

            selected_athlete = next(
                (
                    athlete

                    for athlete
                    in linked_athletes

                    if (
                        str(
                            athlete.id
                        )
                        ==
                        selected_athlete_id
                    )
                ),
                None,
            )


            if (
                selected_athlete
                is None
            ):

                raise Http404(
                    (
                        'This athlete is not linked '
                        'to your account.'
                    )
                )


        else:

            selected_athlete = (
                linked_athletes[0]
            )


    # ========================================================
    # BASE CONTEXT
    # ========================================================

    context = {

        'linked_athletes': (
            linked_athletes
        ),

        'selected_athlete': (
            selected_athlete
        ),

        'dashboard_communication': (
            get_dashboard_communication_data(
                request.user
            )
        ),
    }


    # ========================================================
    # NO LINKED ATHLETE
    # ========================================================

    if (
        selected_athlete
        is None
    ):

        return render(
            request,
            'parents_portal/dashboard.html',
            context,
        )


    today = (
        timezone.now().date()
    )


    # ========================================================
    # WELLNESS
    # ========================================================

    today_survey = (
        DailySurvey.objects
        .filter(
            athlete=(
                selected_athlete
            ),
            survey_date=(
                today
            ),
        )
        .first()
    )


    readiness_status = (
        calculate_parent_readiness_status(
            today_survey
        )
    )


    # ========================================================
    # ATTENDANCE
    # ========================================================

    attendance_records = (
        AttendanceRecord.objects
        .filter(
            athlete=(
                selected_athlete
            ),
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
        +
        attendance_late
    )


    if attendance_total > 0:

        attendance_rate = round(
            (
                attendance_counted
                /
                attendance_total
            )
            *
            100
        )


    else:

        attendance_rate = 0


    # ========================================================
    # PERFORMANCE TESTING
    # ========================================================

    testing_queryset = (
        AthleteTestingResult.objects
        .filter(
            athlete=(
                selected_athlete
            ),
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

        for result
        in testing_results
    ]


    testing_chart_scores = [
        float(
            result.total_score
        )

        for result
        in testing_results
    ]


    testing_score_change = None

    testing_personal_best = None

    testing_trend = (
        'No trend yet'
    )


    if testing_results:

        testing_personal_best = max(
            result.total_score

            for result
            in testing_results
        )


    if (
        latest_testing_result
        and
        len(
            testing_results
        ) >= 2
    ):

        previous_result = (
            testing_results[-2]
        )


        testing_score_change = (
            latest_testing_result.total_score
            -
            previous_result.total_score
        )


        if (
            testing_score_change
            > 0
        ):

            testing_trend = (
                'Trending Up'
            )


        elif (
            testing_score_change
            < 0
        ):

            testing_trend = (
                'Building Consistency'
            )


        else:

            testing_trend = (
                'Holding Steady'
            )


    # ========================================================
    # UPCOMING EVENTS
    # ========================================================

    athlete_membership = (
        GymMembership.objects
        .filter(
            user=selected_athlete,
            role='athlete',
            is_active=True
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
                event_date__gte=today
            )
            .select_related('created_by')
            .order_by(
                'event_date',
                'start_time'
            )[:5]
        )

    else:
        upcoming_events = TeamEvent.objects.none()

    next_event = (
        upcoming_events.first()
        if upcoming_events.exists()
        else None
    )

    days_until_next_event = None

    if next_event:
        days_until_next_event = (
                next_event.event_date
                - today
        ).days
    # ========================================================
    # SHARED VIDEO LIBRARY
    # ========================================================
    #
    # IMPORTANT:
    # We now use video_library.Video,
    # not the old athletes.AthleteVideo model.
    #
    # This includes videos where the selected
    # athlete is:
    #
    # - Primary Athlete
    # - Tagged Athlete
    #
    # AND visibility is Parents.
    #

    parent_videos = (
        get_parent_videos(
            request.user,
            athlete=(
                selected_athlete
            ),
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


    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context.update({

        'today': (
            today
        ),

        'today_survey': (
            today_survey
        ),

        'readiness_status': (
            readiness_status
        ),


        # ----------------------------------------------------
        # Attendance
        # ----------------------------------------------------

        'attendance_total': (
            attendance_total
        ),

        'attendance_present': (
            attendance_present
        ),

        'attendance_late': (
            attendance_late
        ),

        'attendance_rate': (
            attendance_rate
        ),


        # ----------------------------------------------------
        # Testing
        # ----------------------------------------------------

        'latest_testing_result': (
            latest_testing_result
        ),

        'testing_results': (
            testing_results
        ),

        'testing_score_change': (
            testing_score_change
        ),

        'testing_personal_best': (
            testing_personal_best
        ),

        'testing_trend': (
            testing_trend
        ),

        'testing_chart_labels': (
            testing_chart_labels
        ),

        'testing_chart_scores': (
            testing_chart_scores
        ),


        # ----------------------------------------------------
        # Events
        # ----------------------------------------------------

        'upcoming_events': (
            upcoming_events
        ),

        'next_event': (
            next_event
        ),

        'days_until_next_event': (
            days_until_next_event
        ),


        # ----------------------------------------------------
        # NEW VIDEO LIBRARY
        # ----------------------------------------------------

        'parent_videos': (
            parent_videos
        ),

        'recent_parent_videos': (
            recent_parent_videos
        ),

        'parent_video_count': (
            parent_video_count
        ),

        # Compatibility with an older template section.
        # If dashboard.html still uses "recent_videos",
        # it will now receive the NEW Video model videos.
        'recent_videos': (
            recent_parent_videos
        ),
    })


    return render(
        request,
        'parents_portal/dashboard.html',
        context,
    )

@login_required
def parent_video_detail(
    request,
    video_id,
):
    if request.user.role != 'parent':
        messages.error(
            request,
            'Only parents can access this page.',
        )

        return redirect(
            'role_redirect'
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


@login_required
def parent_events(
    request,
):
    if request.user.role != 'parent':

        messages.error(
            request,
            'Only parents can access this page.',
        )

        return redirect(
            'role_redirect'
        )

    today = timezone.now().date()

    upcoming_events = (
        TeamEvent.objects
        .filter(
            event_date__gte=today,
        )
        .order_by(
            'event_date',
            'start_time',
        )
    )

    past_events = (
        TeamEvent.objects
        .filter(
            event_date__lt=today,
        )
        .order_by(
            '-event_date',
            '-start_time',
        )[:10]
    )

    context = {
        'today': today,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'upcoming_event_count': (
            upcoming_events.count()
        ),
    }

    return render(
        request,
        'parents_portal/events.html',
        context,
    )


@login_required
def connect_athlete(request):
    if request.user.role != 'parent':
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': request.user.role,
                'username': request.user.username,
            }
        )

    parent_gym_ids = GymMembership.objects.filter(
        user=request.user,
        role='parent',
        is_active=True,
    ).values_list('gym_id', flat=True)

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
        form = ConnectAthleteForm(request.POST)

        if form.is_valid():
            first_name = form.cleaned_data['first_name'].strip()
            last_name = form.cleaned_data['last_name'].strip()
            date_of_birth = form.cleaned_data['date_of_birth']
            relationship = form.cleaned_data['relationship'].strip()

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
                    'We could not find an athlete matching that name and date of birth in your gym.'
                )

            else:
                athlete = athlete_membership.user

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
                            'This athlete is already connected to your account.'
                        )
                    else:
                        messages.info(
                            request,
                            'Your connection request is already waiting for approval.'
                        )

                    return redirect('connect_athlete')

                ParentAthleteLink.objects.create(
                    parent=request.user,
                    athlete=athlete,
                    relationship=relationship,
                    approved=False,
                )

                messages.success(
                    request,
                    'Connection request sent. A Gym Director must approve it before the athlete appears in your account.'
                )

                return redirect('connect_athlete')

    else:
        form = ConnectAthleteForm()

    return render(
        request,
        'parents_portal/connect_athlete.html',
        {
            'form': form,
            'pending_links': pending_links,
        }
    )