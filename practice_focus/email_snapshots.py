"""Explicit report fields: private coach/survey/testing notes never enter email data."""
from collections import defaultdict
from datetime import timedelta
from django.db.models import Avg, Count
from django.utils import timezone
from athletes.models import AttendanceRecord, AthleteSkill
from performance_testing.models import AthleteTestingResult
from surveys.models import DailySurvey
from skill_tracker.models import SkillResult
from routine_tracker.models import DailyRoutineAttempt
from .models import AthleteFeedback, PersonalMilestone
from .engagement_services import approved
from .report_preferences import show_group_averages

REPORT_TITLES = {
    'weekly': 'Weekly Progress', 'progress': 'Athlete Progress',
    'readiness': 'Team Readiness', 'attendance': 'Attendance',
    'wellness': 'Wellness Summary', 'testing': 'Testing Progress',
    'skills': 'Skill Progress', 'routines': 'Routine Progress',
}


def table(title, headers, rows):
    return {'title': title, 'headers': headers, 'rows': rows}


def snapshot_for_week(summary):
    source = summary.snapshot
    sections = []
    for key, title in [('skills', 'Skill progress'), ('routines', 'Routine progress')]:
        sections.append(table(title, ['Event / skill', 'Wow', 'Hit', 'Attempt', 'Success'], [
            [r['label'], r['wow'], r['hit'], r['attempt'], str(r['success']) + '%'] for r in source.get(key, [])]))
    sections.insert(0, table('This week', ['Total attempts', 'Wow', 'Hit', 'Attempt', 'Previous week attempts'],
        [[source.get(k, 0) for k in ('total', 'wow', 'hit', 'attempt', 'previous_total')]]))
    include_group = show_group_averages(summary.coach, summary.gym_id)
    if include_group and source.get('group'):
        group = source['group']
        sections.append(table('Group average', ['Wow', 'Hit', 'Attempt'], [[group.get('wow', 0), group.get('hit', 0), group.get('missed', 0)]]))
    sections.append(table('Personal milestones', ['Achievement'], [[title] for title in source.get('milestones', [])]))
    feedback = ([summary.coach_feedback] if summary.coach_feedback else []) + list(source.get('shared_feedback', []))
    return {'title': 'Weekly Progress', 'period': f'{summary.week_start} to {summary.week_start + timedelta(days=6)}',
        'sections': sections, 'feedback': feedback, 'athlete_ids': [summary.athlete_id],
        'athlete_name': summary.athlete.get_full_name() or summary.athlete.username,
        'include_group': include_group, 'source_publication': summary.published_at.isoformat()}


def build_snapshot(kind, coach, gym_id, people, start, end):
    people = list(people)
    names = {p.pk: p.get_full_name() or p.username for p in people}
    ids = list(names)
    sections = []
    if kind in ('attendance', 'progress'):
        counts = defaultdict(lambda: defaultdict(int))
        for r in AttendanceRecord.objects.filter(athlete_id__in=ids, attendance_date__range=(start, end)).order_by().values('athlete_id', 'status').annotate(total=Count('pk')):
            counts[r['athlete_id']][r['status']] = r['total']
        rows = []
        for pk in ids:
            c = counts[pk]; total = sum(c.values())
            rate = str(round((c['present'] + c['late']) * 100 / total)) + '%' if total else 'No records'
            rows.append([names[pk], c['present'], c['late'], c['absent'], c['excused'], rate])
        sections.append(table('Attendance', ['Athlete', 'Present', 'Late', 'Absent', 'Excused', 'Attendance rate'], rows))
    if kind in ('wellness', 'progress'):
        surveys = DailySurvey.objects.filter(athlete_id__in=ids, survey_date__range=(start, end))
        averages = {r['athlete_id']: r for r in surveys.order_by().values('athlete_id').annotate(
            count=Count('pk'), energy=Avg('energy'), soreness=Avg('soreness'), stress=Avg('stress'), sleep=Avg('sleep_hours'))}
        rows = []
        for pk in ids:
            r = averages.get(pk, {})
            rows.append([names[pk], r.get('count', 0)] + [round(float(r[k]), 1) if r.get(k) is not None else '—' for k in ('energy', 'soreness', 'stress', 'sleep')])
        sections.append(table('Wellness averages', ['Athlete', 'Surveys', 'Energy / 5', 'Soreness / 5', 'Stress / 5', 'Sleep hours'], rows))
    if kind == 'readiness':
        latest = {}
        for r in DailySurvey.objects.filter(athlete_id__in=ids, survey_date__range=(start, end)).order_by('-survey_date').values('athlete_id', 'survey_date', 'energy', 'soreness', 'stress', 'sleep_hours'):
            latest.setdefault(r['athlete_id'], r)
        rows = []
        for pk in ids:
            r = latest.get(pk)
            rows.append([names[pk]] + ([str(r['survey_date']), r['energy'], r['soreness'], r['stress'], str(r['sleep_hours']) if r['sleep_hours'] is not None else '—'] if r else ['No survey', '—', '—', '—', '—']))
        sections.append(table('Latest wellness check-in', ['Athlete', 'Survey date', 'Energy / 5', 'Soreness / 5', 'Stress / 5', 'Sleep hours'], rows))
    if kind in ('testing', 'progress'):
        results = AthleteTestingResult.objects.filter(athlete_id__in=ids, session__gym_id=gym_id,
            session__testing_date__range=(start, end), status='verified').select_related('session').order_by('athlete_id', 'session__testing_date', 'pk')
        rows = [[names[r.athlete_id], str(r.session.testing_date), r.session.title, str(r.total_score)] for r in results]
        sections.append(table('Verified testing results', ['Athlete', 'Date', 'Session', 'Total score'], rows))
    if kind in ('skills', 'progress'):
        results = approved(SkillResult.objects.filter(assignment__athlete_id__in=ids, assignment__skill__gym_id=gym_id, practice_date__range=(start, end)))
        grouped = defaultdict(lambda: defaultdict(int))
        for r in results.order_by().values('assignment__athlete_id', 'assignment__skill__event', 'assignment__skill__name', 'result').annotate(total=Count('pk')):
            grouped[(r['assignment__athlete_id'], r['assignment__skill__event'], r['assignment__skill__name'])][r['result']] = r['total']
        rows = []
        for (pk, event, skill), c in sorted(grouped.items()):
            total = sum(c.values())
            rows.append([names[pk], event.title(), skill, c['wow'], c['hit'], c['missed'], str(round((c['wow'] + c['hit']) * 100 / total)) + '%'])
        sections.append(table('Approved skill attempts', ['Athlete', 'Event', 'Skill', 'Wow', 'Hit', 'Attempt', 'Success'], rows))
        statuses = AthleteSkill.objects.filter(athlete_id__in=ids,
            coach__gym_memberships__gym_id=gym_id, coach__gym_memberships__is_active=True,
            coach__gym_memberships__role__in=['coach', 'head_coach']).select_related('skill').distinct()
        sections.append(table('Current skill development', ['Athlete', 'Event', 'Skill', 'Status'],
            [[names[r.athlete_id], r.skill.get_event_display(), r.skill.name, r.get_status_display()] for r in statuses]))
    if kind in ('routines', 'progress'):
        results = approved(DailyRoutineAttempt.objects.filter(athlete_id__in=ids, session__gym_id=gym_id, session__practice_date__range=(start, end)))
        grouped = defaultdict(lambda: defaultdict(int))
        for r in results.order_by().values('athlete_id', 'event', 'is_pressure', 'result').annotate(total=Count('pk')):
            grouped[(r['athlete_id'], r['event'], r['is_pressure'])][r['result']] = r['total']
        rows = []
        for (pk, event, pressure), c in sorted(grouped.items()):
            total = sum(c.values())
            rows.append([names[pk], event.title(), 'Pressure set' if pressure else 'Routine', c['wow'], c['hit'], c['missed'], str(round((c['wow'] + c['hit']) * 100 / total)) + '%'])
        sections.append(table('Approved routine attempts', ['Athlete', 'Event', 'Set', 'Wow', 'Hit', 'Attempt', 'Success'], rows))
    feedback = []
    if kind == 'progress' and len(ids) == 1:
        feedback = list(AthleteFeedback.objects.filter(gym_id=gym_id, athlete_id=ids[0], created_at__date__range=(start, end)).exclude(shared_feedback='').values_list('shared_feedback', flat=True))
        sections.append(table('Personal milestones', ['Achievement'], [[title] for title in PersonalMilestone.objects.filter(
            gym_id=gym_id, athlete_id=ids[0], practice_date__range=(start, end), active=True).values_list('title', flat=True)]))
    return {'title': REPORT_TITLES[kind], 'period': f'{start} to {end}', 'sections': sections,
        'feedback': feedback, 'athlete_ids': ids, 'athlete_name': names[ids[0]] if len(ids) == 1 else 'Coaching roster',
        'include_group': False}
