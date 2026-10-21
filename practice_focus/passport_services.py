from django.db.models import Count
from athletes.models import AttendanceRecord
from skill_tracker.models import SkillResult
from routine_tracker.models import DailyRoutineAttempt
from .models import AthletePracticePlan
from .engagement_services import approved
from .passport_models import PassportStamp
from .passport_badge_services import badge_catalog


def passport_metrics(gym_id, athlete_id, through):
    """Read-only progress; pending/rejected/undone tracker entries never earn eligibility."""
    skills = approved(SkillResult.objects.filter(assignment__athlete_id=athlete_id,
        assignment__skill__gym_id=gym_id, practice_date__lte=through))
    routines = approved(DailyRoutineAttempt.objects.filter(athlete_id=athlete_id,
        session__gym_id=gym_id, session__practice_date__lte=through))
    skill_counts = {(r['practice_date'], r['assignment__skill__event'], r['assignment__skill_id']): r['total']
        for r in skills.order_by().values('practice_date', 'assignment__skill__event', 'assignment__skill_id').annotate(total=Count('pk'))}
    routine_counts = {(r['session__practice_date'], r['event'], r['is_pressure']): r['total']
        for r in routines.order_by().values('session__practice_date', 'event', 'is_pressure').annotate(total=Count('pk'))}
    practice_days = {k[0] for k in skill_counts} | {k[0] for k in routine_counts}
    goals, routine_days, events = set(), set(), set()
    for plan in AthletePracticePlan.objects.filter(gym_id=gym_id, athlete_id=athlete_id, practice_date__lte=through):
        content = plan.content if isinstance(plan.content, dict) else {}
        for event in ('vault', 'bars', 'beam', 'floor'):
            details = content.get(event, {})
            if not isinstance(details, dict):
                continue
            planned = details.get('skills', [])
            for item in planned if isinstance(planned, list) else []:
                if not isinstance(item, dict):
                    continue
                target, skill_id = item.get('target'), item.get('id')
                if type(skill_id) is int and type(target) is int and target > 0 and skill_counts.get((plan.practice_date, event, skill_id), 0) >= target:
                    goals.add((plan.practice_date, 'skill', skill_id)); events.add(event)
            for key, pressure in [('routines', False), ('pressure', True)]:
                target = details.get(key)
                if type(target) is int and target > 0 and routine_counts.get((plan.practice_date, event, pressure), 0) >= target:
                    goals.add((plan.practice_date, event, key)); events.add(event)
                    if not pressure:
                        routine_days.add(plan.practice_date)
    attended = AttendanceRecord.objects.filter(athlete_id=athlete_id, attendance_date__lte=through,
        status__in=['present', 'late'], coach__gym_memberships__gym_id=gym_id,
        coach__gym_memberships__role__in=['coach', 'head_coach']).values('attendance_date').distinct().count()
    data = {'practice_days': len(practice_days), 'goals': len(goals), 'routine_days': len(routine_days),
            'attendance': attended, 'wow': int(skills.filter(result='wow').exists() or routines.filter(result='wow').exists())}
    data.update({'event:' + event: int(event in events) for event in ('vault', 'bars', 'beam', 'floor')})
    return data


def stamp_ready(definition, metrics):
    return definition['manual'] or metrics.get(definition['metric'], 0) >= definition['target']


def passport_cards(gym_id, athlete_id, metrics, staff=False, catalog=None):
    query = PassportStamp.objects.filter(gym_id=gym_id, athlete_id=athlete_id)
    if not staff:
        query = query.filter(revoked_at__isnull=True)
    records = {r.badge_code + ':' + r.variant: r for r in query.select_related('awarded_by')}
    cards = []
    catalog = catalog if catalog is not None else badge_catalog(gym_id, include_archived=True, include_deleted=True)
    for slot, definition in catalog.items():
        record = records.get(slot)
        earned = bool(record and not record.revoked_at)
        if not definition['is_active'] and not earned:
            continue
        display = {**definition, **record.badge_snapshot} if earned and record.badge_snapshot else definition
        count = metrics.get(definition['metric'], 0)
        award = {'id': record.pk, 'version': record.version, 'date': record.award_date,
                 'note': record.shared_note, 'coach': record.awarded_by.get_full_name() or record.awarded_by.username} if earned else None
        cards.append({**display, 'earned': earned, 'award': award, 'ready': definition['is_active'] and stamp_ready(definition, metrics),
            'count': count, 'progress': min(count, definition['target']),
            'percent': min(100, round(count * 100 / definition['target'])) if definition['target'] else 0,
            'version': record.version if record else 0})
    return cards
