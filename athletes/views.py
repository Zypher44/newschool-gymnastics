from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from coaches.models import TeamEvent
from performance_testing.models import AthleteTestingResult
from surveys.models import DailySurvey

from .models import (
    AttendanceRecord,
    AthleteProfile,
    AthleteVideo,
)


def calculate_athlete_readiness(survey):
    if not survey:
        return None

    if (
            survey.energy == 1
            or survey.soreness == 5
            or survey.stress == 5
            or (
            survey.sleep_hours is not None
            and survey.sleep_hours < 6
    )
    ):
        return 25

    if (
            survey.energy == 2
            or survey.soreness == 4
            or survey.stress == 4
            or (
            survey.sleep_hours is not None
            and survey.sleep_hours < 7
    )
    ):
        return 50

    if (
            survey.energy == 3
            or survey.soreness == 3
            or survey.stress == 3
            or (
            survey.sleep_hours is not None
            and survey.sleep_hours < 8
    )
    ):
        return 75

    return 100


@login_required
def athlete_dashboard(request):
    if request.user.role != 'athlete':
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete = request.user
    today = timezone.now().date()

    athlete_profile = AthleteProfile.objects.filter(
        user=athlete
    ).first()

    today_survey = DailySurvey.objects.filter(
        athlete=athlete,
        survey_date=today
    ).first()

    readiness_score = calculate_athlete_readiness(
        today_survey
    )

    recent_surveys = DailySurvey.objects.filter(
        athlete=athlete
    ).order_by(
        '-survey_date'
    )[:7]

    survey_dates = set(
        DailySurvey.objects.filter(
            athlete=athlete,
            survey_date__lte=today
        ).values_list(
            'survey_date',
            flat=True
        )
    )

    survey_streak = 0
    streak_date = today

    while streak_date in survey_dates:
        survey_streak += 1
        streak_date -= timezone.timedelta(days=1)

    upcoming_events = TeamEvent.objects.filter(
        event_date__gte=today
    ).order_by(
        'event_date',
        'start_time'
    )[:5]

    recent_videos = AthleteVideo.objects.filter(
        athlete=athlete
    ).exclude(
        review_status='not_reviewed'
    ).select_related(
        'skill',
        'uploaded_by'
    ).order_by(
        '-uploaded_at'
    )[:4]

    latest_testing_result = (
        AthleteTestingResult.objects.filter(
            athlete=athlete,
            status='verified',
            session__published_to_athletes=True
        )
        .select_related(
            'session',
            'verified_by'
        )
        .order_by(
            '-session__testing_date',
            '-session__created_at'
        )
        .first()
    )

    testing_results = list(
        AthleteTestingResult.objects.filter(
            athlete=athlete,
            status='verified',
            session__published_to_athletes=True
        )
        .select_related('session')
        .order_by('session__testing_date')
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

    if latest_testing_result:
        previous_result = (
            latest_testing_result.get_previous_result()
        )

        if previous_result:
            testing_score_change = (
                    latest_testing_result.total_score
                    - previous_result.total_score
            )

        if testing_results:
            testing_personal_best = max(
                result.total_score
                for result in testing_results
            )

    attendance_records = AttendanceRecord.objects.filter(
        athlete=athlete
    )

    attendance_total = attendance_records.count()

    attendance_present = attendance_records.filter(
        status='present'
    ).count()

    attendance_late = attendance_records.filter(
        status='late'
    ).count()

    if attendance_total > 0:
        attendance_rate = round(
            (
                    (
                            attendance_present
                            + attendance_late
                    )
                    / attendance_total
            )
            * 100
        )
    else:
        attendance_rate = 0

    next_event = (
        upcoming_events[0]
        if upcoming_events
        else None
    )

    return render(
        request,
        'athletes/dashboard.html',
        {
            'athlete': athlete,
            'athlete_profile': athlete_profile,
            'today': today,
            'today_survey': today_survey,
            'readiness_score': readiness_score,
            'recent_surveys': recent_surveys,
            'upcoming_events': upcoming_events,
            'next_event': next_event,
            'recent_videos': recent_videos,
            'latest_testing_result': latest_testing_result,
            'testing_score_change': testing_score_change,
            'testing_personal_best': testing_personal_best,
            'testing_chart_labels': testing_chart_labels,
            'testing_chart_scores': testing_chart_scores,
            'attendance_total': attendance_total,
            'attendance_rate': attendance_rate,
            'survey_streak': survey_streak,
        }
    )


from django.shortcuts import render

# Create your views here.
