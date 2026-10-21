from datetime import datetime
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from gyms.models import TrainingGroupAthlete
from gyms.tenant import single_active_gym_id
from routine_tracker.models import DailyRoutineAttempt

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
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return default_value


def routine_comparison_rows(user, selected_athlete, allowed_athletes, start_date, end_date):
    """Compare an athlete with peers from their coach-assigned training group(s)."""
    gym_id = single_active_gym_id(user, ['coach', 'head_coach'])
    if not gym_id:
        return []

    if not allowed_athletes.filter(pk=selected_athlete.pk, is_active=True, role='athlete', gym_memberships__gym_id=gym_id, gym_memberships__role='athlete', gym_memberships__is_active=True).exists():
        return []
    from practice_focus.report_preferences import show_group_averages
    include_group_averages = show_group_averages(user, gym_id)
    if include_group_averages:
        group_ids = list(TrainingGroupAthlete.objects.filter(
            athlete=selected_athlete,
            is_active=True,
            group__gym_id=gym_id,
            group__is_active=True,
            group__coach_assignments__coach=user,
        ).values_list('group_id', flat=True).distinct())
    
        peer_ids = set(allowed_athletes.filter(is_active=True, role='athlete', gym_memberships__gym_id=gym_id, gym_memberships__role='athlete', gym_memberships__is_active=True).values_list('pk', flat=True))
        if group_ids:
            group_peer_ids = set(TrainingGroupAthlete.objects.filter(
                group_id__in=group_ids,
                group__gym_id=gym_id,
                is_active=True,
                athlete__is_active=True,
            ).values_list('athlete_id', flat=True))
            peer_ids &= group_peer_ids
        if selected_athlete.pk not in peer_ids:
            peer_ids.add(selected_athlete.pk)
    else:
        peer_ids = {selected_athlete.pk}

    rows = defaultdict(lambda: defaultdict(int))
    aggregates = DailyRoutineAttempt.objects.filter(
        session__gym_id=gym_id,
        session__practice_date__range=(start_date, end_date),
        athlete_id__in=peer_ids,
    ).values('athlete_id', 'event', 'is_pressure', 'result').annotate(total=Count('pk'))
    for item in aggregates:
        rows[(item['event'], item['is_pressure'])][(item['athlete_id'], item['result'])] = item['total']

    results = [
        (DailyRoutineAttempt.RESULT_WOW, 'Wow'),
        (DailyRoutineAttempt.RESULT_HIT, 'Hit'),
        (DailyRoutineAttempt.RESULT_MISSED, 'Attempt'),
    ]
    output = []
    for event, event_label in DailyRoutineAttempt.EVENT_CHOICES:
        for is_pressure in (False, True):
            per_athlete = {
                athlete_id: {
                    result: rows[(event, is_pressure)].get((athlete_id, result), 0)
                    for result, _ in results
                }
                for athlete_id in peer_ids
            }
            active_peers = [
                counts for counts in per_athlete.values()
                if sum(counts.values()) > 0
            ]
            child = per_athlete.get(selected_athlete.pk, {result: 0 for result, _ in results})
            child_total = sum(child.values())
            group_totals = {
                result: sum(counts[result] for counts in active_peers)
                for result, _ in results
            }
            group_total = sum(group_totals.values())
            if not child_total and not group_total:
                continue
            output.append({
                'event': event_label,
                'is_pressure': is_pressure,
                'context': 'Pressure set' if is_pressure else 'Routine',
                'athlete_counts': child,
                'athlete_total': child_total,
                'athlete_rates': {
                    result: round(child[result] * 100 / child_total) if child_total else 0
                    for result, _ in results
                },
                'group_average': {
                    result: round(group_totals[result] / len(active_peers), 1) if active_peers else 0
                    for result, _ in results
                },
                'group_rates': {
                    result: round(group_totals[result] * 100 / group_total) if group_total else 0
                    for result, _ in results
                },
                'group_athletes': len(active_peers),
            })
    # V3 coach report preferences
    if not include_group_averages:
        for row in output:
            for key in ('group_average', 'group_rates', 'group_athletes'):
                row.pop(key, None)
    return output


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

    # V3 practice progress upgrades
    report_cards.append({'title':'Weekly Reports','description':'Preview and publish weekly skill and routine progress summaries for parents.','icon':'','url_name':'practice_focus:weekly_reports','badge':'Coach approved'})

    # V3 passport report-card repair
    if not any(card.get('url_name') == 'practice_focus:coach_passport' for card in report_cards):
        report_cards.append({
            'title': 'Practice Passports',
            'description': 'Award badges for effort, attendance and personal progress. View each athlete’s practice passport.',
            'icon': '🏅',
            'url_name': 'practice_focus:coach_passport',
            'badge': 'Coach awarded',
        })
    
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

    athletes = get_allowed_athletes(request.user)
    gym_id = single_active_gym_id(request.user, ['coach', 'head_coach'])
    if gym_id is None:
        athletes = athletes.none()
    else:
        athletes = athletes.filter(
            gym_memberships__gym_id=gym_id,
            gym_memberships__role='athlete',
            gym_memberships__is_active=True,
        ).distinct()

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
    routine_comparison = []
    from practice_focus.report_preferences import show_group_averages
    include_group_averages = show_group_averages(request.user, gym_id)
    skill_comparison = None

    if selected_athlete:
        report_data = get_athlete_progress_data(
            athlete=selected_athlete,
            start_date=start_date,
            end_date=end_date
        )
        routine_comparison = routine_comparison_rows(
            request.user,
            selected_athlete,
            athletes,
            start_date,
            end_date,
        )
        from .services.skill_progress import skill_comparison_data
        skill_comparison = skill_comparison_data(
            request.user, selected_athlete, athletes, gym_id, start_date, end_date,
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
            'routine_comparison': routine_comparison,
            'skill_comparison': skill_comparison,
            'show_group_averages': include_group_averages,
        }
    )


@login_required
def team_readiness_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return report_email_preview(request, kind='readiness')


@login_required
def attendance_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return report_email_preview(request, kind='attendance')


@login_required
def wellness_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return report_email_preview(request, kind='wellness')


@login_required
def testing_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return report_email_preview(request, kind='testing')


@login_required
def skill_report(request):
    if not coach_report_access_required(request):
        return render_report_denied(request)

    return report_email_preview(request, kind='skills')


# V3 report email delivery
from practice_focus.email_views import email_report_preview as report_email_preview
