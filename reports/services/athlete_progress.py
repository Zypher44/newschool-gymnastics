from datetime import timedelta

from django.utils import timezone

from athletes.models import (
    AttendanceRecord,
    AthleteProfile,
    AthleteVideo,
)
from coaches.models import (
    CoachAthleteAssignment,
    CoachNote,
    TeamEvent,
)
from performance_testing.models import AthleteTestingResult
from surveys.models import DailySurvey


def get_allowed_athletes(user):
    """
    Return athletes that the logged-in coach may report on.

    Head coaches can view all athletes.
    Regular coaches can view assigned athletes only.
    """

    from accounts.models import User

    if user.role == 'head_coach':
        return (
            User.objects
            .filter(role='athlete')
            .order_by(
                'first_name',
                'last_name',
                'username'
            )
        )

    athlete_ids = (
        CoachAthleteAssignment.objects
        .filter(coach=user)
        .values_list(
            'athlete_id',
            flat=True
        )
    )

    return (
        User.objects
        .filter(
            id__in=athlete_ids,
            role='athlete'
        )
        .order_by(
            'first_name',
            'last_name',
            'username'
        )
    )


def calculate_average(values):
    clean_values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not clean_values:
        return None

    return round(
        sum(clean_values) / len(clean_values),
        1
    )


def calculate_attendance_summary(
    athlete,
    start_date,
    end_date
):
    records = (
        AttendanceRecord.objects
        .filter(
            athlete=athlete,
            attendance_date__range=[
                start_date,
                end_date,
            ]
        )
        .order_by('-attendance_date')
    )

    total = records.count()

    present = records.filter(
        status='present'
    ).count()

    late = records.filter(
        status='late'
    ).count()

    absent = records.filter(
        status='absent'
    ).count()

    excused = records.filter(
        status='excused'
    ).count()

    attended = present + late

    if total:
        attendance_rate = round(
            attended / total * 100
        )
    else:
        attendance_rate = 0

    return {
        'records': records[:15],
        'total': total,
        'present': present,
        'late': late,
        'absent': absent,
        'excused': excused,
        'attended': attended,
        'attendance_rate': attendance_rate,
    }


def calculate_wellness_summary(
    athlete,
    start_date,
    end_date
):
    surveys = list(
        DailySurvey.objects
        .filter(
            athlete=athlete,
            survey_date__range=[
                start_date,
                end_date,
            ]
        )
        .order_by('survey_date')
    )

    energy_values = [
        survey.energy
        for survey in surveys
    ]

    soreness_values = [
        survey.soreness
        for survey in surveys
    ]

    stress_values = [
        survey.stress
        for survey in surveys
    ]

    sleep_values = [
        survey.sleep_hours
        for survey in surveys
    ]

    survey_chart_labels = [
        survey.survey_date.strftime('%b %d')
        for survey in surveys
    ]

    energy_chart_values = [
        survey.energy
        for survey in surveys
    ]

    soreness_chart_values = [
        survey.soreness
        for survey in surveys
    ]

    stress_chart_values = [
        survey.stress
        for survey in surveys
    ]

    sleep_chart_values = [
        (
            float(survey.sleep_hours)
            if survey.sleep_hours is not None
            else None
        )
        for survey in surveys
    ]

    low_energy_days = len([
        survey
        for survey in surveys
        if survey.energy <= 2
    ])

    high_soreness_days = len([
        survey
        for survey in surveys
        if survey.soreness >= 4
    ])

    high_stress_days = len([
        survey
        for survey in surveys
        if survey.stress >= 4
    ])

    low_sleep_days = len([
        survey
        for survey in surveys
        if (
            survey.sleep_hours is not None
            and survey.sleep_hours < 7
        )
    ])

    latest_survey = (
        surveys[-1]
        if surveys
        else None
    )

    return {
        'surveys': surveys,
        'survey_count': len(surveys),
        'latest_survey': latest_survey,

        'average_energy': calculate_average(
            energy_values
        ),

        'average_soreness': calculate_average(
            soreness_values
        ),

        'average_stress': calculate_average(
            stress_values
        ),

        'average_sleep': calculate_average(
            sleep_values
        ),

        'low_energy_days': low_energy_days,
        'high_soreness_days': high_soreness_days,
        'high_stress_days': high_stress_days,
        'low_sleep_days': low_sleep_days,

        'survey_chart_labels': survey_chart_labels,
        'energy_chart_values': energy_chart_values,
        'soreness_chart_values': soreness_chart_values,
        'stress_chart_values': stress_chart_values,
        'sleep_chart_values': sleep_chart_values,
    }


def calculate_testing_summary(
    athlete,
    start_date,
    end_date
):
    results = list(
        AthleteTestingResult.objects
        .filter(
            athlete=athlete,
            status='verified',
            session__testing_date__range=[
                start_date,
                end_date,
            ]
        )
        .select_related(
            'session',
            'verified_by'
        )
        .order_by(
            'session__testing_date',
            'session__created_at'
        )
    )

    latest_result = (
        results[-1]
        if results
        else None
    )

    previous_result = (
        results[-2]
        if len(results) >= 2
        else None
    )

    score_change = None

    if latest_result and previous_result:
        score_change = (
            latest_result.total_score
            - previous_result.total_score
        )

    personal_best = None

    if results:
        personal_best = max(
            result.total_score
            for result in results
        )

    testing_chart_labels = [
        result.session.testing_date.strftime(
            '%b %d'
        )
        for result in results
    ]

    testing_chart_scores = [
        float(result.total_score)
        for result in results
    ]

    return {
        'testing_results': results,
        'latest_testing_result': latest_result,
        'previous_testing_result': previous_result,
        'testing_score_change': score_change,
        'testing_personal_best': personal_best,
        'testing_chart_labels': testing_chart_labels,
        'testing_chart_scores': testing_chart_scores,
    }


def get_athlete_progress_data(
    *,
    athlete,
    start_date,
    end_date
):
    today = timezone.now().date()

    athlete_profile = (
        AthleteProfile.objects
        .filter(user=athlete)
        .first()
    )

    attendance = calculate_attendance_summary(
        athlete,
        start_date,
        end_date
    )

    wellness = calculate_wellness_summary(
        athlete,
        start_date,
        end_date
    )

    testing = calculate_testing_summary(
        athlete,
        start_date,
        end_date
    )

    coach_notes = (
        CoachNote.objects
        .filter(
            athlete=athlete,
            created_at__date__range=[
                start_date,
                end_date,
            ]
        )
        .select_related('coach')
        .order_by('-created_at')[:10]
    )

    recent_videos = (
        AthleteVideo.objects
        .filter(
            athlete=athlete,
            uploaded_at__date__range=[
                start_date,
                end_date,
            ]
        )
        .exclude(
            review_status='not_reviewed'
        )
        .select_related(
            'skill',
            'uploaded_by'
        )
        .order_by('-uploaded_at')[:8]
    )

    upcoming_events = (
        TeamEvent.objects
        .filter(event_date__gte=today)
        .order_by(
            'event_date',
            'start_time'
        )[:5]
    )

    return {
        'athlete_profile': athlete_profile,
        'attendance': attendance,
        'wellness': wellness,
        'testing': testing,
        'coach_notes': coach_notes,
        'recent_videos': recent_videos,
        'upcoming_events': upcoming_events,
    }


def default_report_dates():
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=90)

    return start_date, end_date