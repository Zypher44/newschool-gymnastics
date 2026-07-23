from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from .services.athlete_progress import (
    default_report_dates,
    get_allowed_athletes,
    get_athlete_progress_data,
)


def coach_report_access_required(request):
    return request.user.role in [
        'coach',
        'head_coach',
    ]


def render_report_denied(request):
    return render(
        request,
        'coaches/not_allowed.html',
        {
            'role': request.user.role,
            'username': request.user.username,
        }
    )


def parse_report_date(
    value,
    default_value
):
    if not value:
        return default_value

    try:
        return datetime.strptime(
            value,
            '%Y-%m-%d'
        ).date()

    except ValueError:
        return default_value


@login_required
def report_center(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    report_cards = [
        {
            'title': 'Athlete Progress',
            'description': (
                'View a complete athlete summary including attendance, '
                'wellness, testing and coach feedback.'
            ),
            'icon': '🤸',
            'url_name': 'athlete_progress_report',
            'badge': 'Complete Overview',
        },
        {
            'title': 'Team Readiness',
            'description': (
                'Review current team readiness, wellness flags and '
                'daily survey completion.'
            ),
            'icon': '⚡',
            'url_name': 'team_readiness_report',
            'badge': 'Daily',
        },
        {
            'title': 'Attendance',
            'description': (
                'Analyze attendance rates, absences, late arrivals '
                'and athlete participation.'
            ),
            'icon': '✅',
            'url_name': 'attendance_report',
            'badge': 'Attendance',
        },
        {
            'title': 'Wellness Summary',
            'description': (
                'Track energy, soreness, stress, sleep and survey '
                'submission patterns.'
            ),
            'icon': '💚',
            'url_name': 'wellness_report',
            'badge': 'Wellness',
        },
        {
            'title': 'Testing Progress',
            'description': (
                'Compare testing results, personal bests and '
                'improvement over time.'
            ),
            'icon': '📊',
            'url_name': 'testing_report',
            'badge': 'Performance',
        },
        {
            'title': 'Skill Progress',
            'description': (
                'Review mastered skills, competition-ready skills '
                'and team development by event.'
            ),
            'icon': '🏆',
            'url_name': 'skill_report',
            'badge': 'Skills',
        },
    ]

    return render(
        request,
        'reports/report_center.html',
        {
            'report_cards': report_cards,
        }
    )


@login_required
def athlete_progress_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    athletes = get_allowed_athletes(
        request.user
    )

    default_start_date, default_end_date = (
        default_report_dates()
    )

    start_date = parse_report_date(
        request.GET.get('start_date'),
        default_start_date
    )

    end_date = parse_report_date(
        request.GET.get('end_date'),
        default_end_date
    )

    if start_date > end_date:
        start_date, end_date = (
            end_date,
            start_date
        )

    selected_athlete = None
    selected_athlete_id = request.GET.get(
        'athlete'
    )

    if selected_athlete_id:
        selected_athlete = athletes.filter(
            id=selected_athlete_id
        ).first()

        if selected_athlete is None:
            raise Http404(
                'Athlete not found or not assigned to you.'
            )

    elif athletes.exists():
        selected_athlete = athletes.first()

    report_data = None

    if selected_athlete:
        report_data = get_athlete_progress_data(
            athlete=selected_athlete,
            start_date=start_date,
            end_date=end_date
        )

    return render(
        request,
        'reports/athlete_progress.html',
        {
            'athletes': athletes,
            'selected_athlete': selected_athlete,
            'start_date': start_date,
            'end_date': end_date,
            'report_data': report_data,
        }
    )


@login_required
def team_readiness_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return render(
        request,
        'reports/report_placeholder.html',
        {
            'report_title': (
                'Team Readiness Report'
            ),
            'report_icon': '⚡',
        }
    )


@login_required
def attendance_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return render(
        request,
        'reports/report_placeholder.html',
        {
            'report_title': 'Attendance Report',
            'report_icon': '✅',
        }
    )


@login_required
def wellness_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return render(
        request,
        'reports/report_placeholder.html',
        {
            'report_title': 'Wellness Summary',
            'report_icon': '💚',
        }
    )


@login_required
def testing_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return render(
        request,
        'reports/report_placeholder.html',
        {
            'report_title': (
                'Testing Progress Report'
            ),
            'report_icon': '📊',
        }
    )


@login_required
def skill_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return render(
        request,
        'reports/report_placeholder.html',
        {
            'report_title': (
                'Skill Progress Report'
            ),
            'report_icon': '🏆',
        }
    )
