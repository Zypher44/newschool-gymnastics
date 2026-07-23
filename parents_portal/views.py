from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from athletes.models import AttendanceRecord, AthleteVideo
from coaches.models import TeamEvent
from performance_testing.models import AthleteTestingResult
from surveys.models import DailySurvey

from .models import ParentAthleteLink
from communications.dashboard import (
    get_dashboard_communication_data,
)

def calculate_parent_readiness_status(survey):
    """
    Return a parent-friendly wellness status.

    Parents receive a simple summary rather than detailed
    athlete wellness responses or internal coaching alerts.
    """
    if not survey:
        return {
            'label': 'Survey Not Completed',
            'level': 'unknown',
            'icon': '📝',
            'message': (
                'Today’s wellness survey has not been completed yet.'
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
                'Your child reported that they may need some extra '
                'support today. Their coach can review the details.'
            ),
        }

    return {
        'label': 'Ready to Train',
        'level': 'ready',
        'icon': '🟢',
        'message': (
            'Today’s wellness survey indicates that your child '
            'is ready for training.'
        ),
    }


def get_parent_links(user):
    """
    Return all athlete links belonging to the logged-in parent.

    This assumes ParentAthleteLink contains:
    - parent
    - athlete
    """
    return (
        ParentAthleteLink.objects
        .filter(parent=user)
        .select_related('athlete')
        .order_by(
            'athlete__first_name',
            'athlete__username'
        )
    )


@login_required
def parent_dashboard(request):
    if request.user.role != 'parent':
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': request.user.role,
                'username': request.user.username,
            }
        )

    links = get_parent_links(request.user)

    linked_athletes = [
        link.athlete
        for link in links
    ]

    selected_athlete = None
    selected_athlete_id = request.GET.get('athlete')

    if linked_athletes:
        if selected_athlete_id:
            selected_athlete = next(
                (
                    athlete
                    for athlete in linked_athletes
                    if str(athlete.id) == selected_athlete_id
                ),
                None
            )

            if selected_athlete is None:
                raise Http404(
                    'This athlete is not linked to your account.'
                )
        else:
            selected_athlete = linked_athletes[0]

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
            context
        )

    today = timezone.now().date()

    today_survey = (
        DailySurvey.objects
        .filter(
            athlete=selected_athlete,
            survey_date=today
        )
        .first()
    )

    readiness_status = calculate_parent_readiness_status(
        today_survey
    )

    attendance_records = AttendanceRecord.objects.filter(
        athlete=selected_athlete
    )

    attendance_total = attendance_records.count()

    attendance_present = attendance_records.filter(
        status='present'
    ).count()

    attendance_late = attendance_records.filter(
        status='late'
    ).count()

    attendance_counted = (
        attendance_present
        + attendance_late
    )

    if attendance_total > 0:
        attendance_rate = round(
            attendance_counted
            / attendance_total
            * 100
        )
    else:
        attendance_rate = 0

    testing_queryset = (
        AthleteTestingResult.objects
        .filter(
            athlete=selected_athlete,
            status='verified',
            session__published_to_parents=True
        )
        .select_related(
            'session',
            'verified_by'
        )
    )

    latest_testing_result = (
        testing_queryset
        .order_by(
            '-session__testing_date',
            '-session__created_at'
        )
        .first()
    )

    testing_results = list(
        testing_queryset
        .order_by(
            'session__testing_date',
            'session__created_at'
        )
    )

    testing_chart_labels = [
        result.session.testing_date.strftime('%b %d')
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
        previous_result = testing_results[-2]

        testing_score_change = (
            latest_testing_result.total_score
            - previous_result.total_score
        )

        if testing_score_change > 0:
            testing_trend = 'Trending Up'
        elif testing_score_change < 0:
            testing_trend = 'Building Consistency'
        else:
            testing_trend = 'Holding Steady'

    upcoming_events = (
        TeamEvent.objects
        .filter(
            event_date__gte=today
        )
        .order_by(
            'event_date',
            'start_time'
        )[:5]
    )

    next_event = (
        upcoming_events[0]
        if upcoming_events
        else None
    )

    days_until_next_event = None

    if next_event:
        days_until_next_event = (
            next_event.event_date
            - today
        ).days

    recent_videos = (
        AthleteVideo.objects
        .filter(
            athlete=selected_athlete
        )
        .exclude(
            review_status='not_reviewed'
        )
        .select_related(
            'skill',
            'uploaded_by'
        )
        .order_by(
            '-uploaded_at'
        )[:4]
    )

    context.update({
        'today': today,
        'today_survey': today_survey,
        'readiness_status': readiness_status,

        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_late': attendance_late,
        'attendance_rate': attendance_rate,

        'latest_testing_result': latest_testing_result,
        'testing_results': testing_results,
        'testing_score_change': testing_score_change,
        'testing_personal_best': testing_personal_best,
        'testing_trend': testing_trend,
        'testing_chart_labels': testing_chart_labels,
        'testing_chart_scores': testing_chart_scores,

        'upcoming_events': upcoming_events,
        'next_event': next_event,
        'days_until_next_event': days_until_next_event,

        'recent_videos': recent_videos,
    })

    return render(
        request,
        'parents_portal/dashboard.html',
        context
    )