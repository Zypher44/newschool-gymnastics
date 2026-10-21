from collections import defaultdict
from urllib.parse import urlencode
from django.db.models import Count
from django.urls import reverse
from athletes.models import AttendanceRecord
from practice_focus.models import AthletePracticePlan, TrackedResult
from routine_tracker.models import DailyRoutineAttempt
from skill_tracker.models import Assignment, SkillResult


def link(name, **query):
    return reverse(name) + ('?' + urlencode({k: v for k, v in query.items() if v is not None and v != ''}) if query else '')


def positive(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return 0


def athlete_rows(gym_id, roster, day, event, group, session=None):
    people = list(roster)
    ids = [p.pk for p in people]
    plans = {p.athlete_id: p for p in AthletePracticePlan.objects.filter(
        gym_id=gym_id, athlete_id__in=ids, practice_date=day)}
    attendance = {r.athlete_id: r for r in AttendanceRecord.objects.filter(
        athlete_id__in=ids, attendance_date=day)}
    active = defaultdict(list)
    for a in Assignment.objects.filter(athlete_id__in=ids, skill__gym_id=gym_id,
            skill__event=event, is_active=True).select_related('skill').order_by('skill__name', 'pk'):
        active[a.athlete_id].append(a)
    counts = {(r['assignment__athlete_id'], r['assignment__skill_id']): r['total'] for r in
        SkillResult.objects.filter(assignment__athlete_id__in=ids, assignment__skill__gym_id=gym_id,
            assignment__skill__event=event, practice_date=day).order_by().values(
                'assignment__athlete_id', 'assignment__skill_id').annotate(total=Count('pk'))}
    routines = {(r['athlete_id'], r['is_pressure']): r['total'] for r in
        DailyRoutineAttempt.objects.filter(athlete_id__in=ids, session__gym_id=gym_id,
            session__practice_date=day, event=event).order_by().values(
                'athlete_id', 'is_pressure').annotate(total=Count('pk'))}
    pending = {r['athlete_id']: r['total'] for r in TrackedResult.objects.filter(
        gym_id=gym_id, athlete_id__in=ids, practice_date=day, status='pending'
        ).order_by().values('athlete_id').annotate(total=Count('pk'))}
    from surveys.models import DailySurvey
    surveys = {s.athlete_id: s for s in DailySurvey.objects.filter(athlete_id__in=ids, survey_date=day).select_related("help_skill__skill")}
    from parents_portal.models import PracticeAbsenceNotice
    notices = {n.athlete_id: n for n in PracticeAbsenceNotice.objects.filter(gym_id=gym_id, athlete_id__in=ids, practice_date=day).exclude(status="cancelled")}
    rows = []
    for person in people:
        plan = plans.get(person.pk)
        content = plan.content.get(event, {}) if plan and isinstance(plan.content, dict) else {}
        if not isinstance(content, dict):
            content = {}
        assignments = {a.skill_id: a for a in active[person.pk]}
        planned = content.get('skills', [])
        if not isinstance(planned, list):
            planned = []
        skills = []
        for item in planned:
            if not isinstance(item, dict):
                continue
            skill_id = positive(item.get('id'))
            assignment = assignments.get(skill_id)
            target = positive(item.get('target'))
            completed = counts.get((person.pk, skill_id), 0)
            skills.append({'name': item.get('name') or (assignment.skill.name if assignment else 'Planned skill'),
                'target': target, 'completed': completed, 'active': bool(assignment),
                'met': bool(target and completed >= target)})
        if not plan:
            skills = [{'name': a.skill.name, 'target': 0, 'completed': counts.get((person.pk, a.skill_id), 0),
                'active': True, 'met': False} for a in assignments.values()]
        extra = [a.skill.name for a in assignments.values() if a.skill_id not in {
            positive(s.get('id')) for s in planned if isinstance(s, dict)}] if plan else []
        record = attendance.get(person.pk)
        query = {'group': group.pk, 'athlete': person.pk, 'event': event}
        if session and not session.finished_at:
            query['practice_session'] = session.pk
        row = {'parent_notice': notices.get(person.pk), 'survey': surveys.get(person.pk), 'athlete': person, 'plan': plan, 'skills': skills, 'extra_skills': extra,
            'cue': content.get('cue', ''), 'routine_target': positive(content.get('routines')),
            'pressure_target': positive(content.get('pressure')),
            'routine_completed': routines.get((person.pk, False), 0),
            'pressure_completed': routines.get((person.pk, True), 0),
            'pending': pending.get(person.pk, 0), 'attendance': record,
            'attendance_version': record.updated_at.isoformat() if record else '',
            'skill_url': link('skill_tracker:tracker', **query),
            'routine_url': link('routine_tracker:daily_routine_tracker', **query),
            'plan_url': link('practice_focus:planner', athlete=person.pk, group=group.pk, date=day.isoformat()),
            'feedback_url': link('practice_focus:coach_feedback', athlete=person.pk)}
        rows.append(row)
    return rows
