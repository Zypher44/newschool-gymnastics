from collections import defaultdict
from datetime import timedelta
from uuid import uuid4
from django.db.models import Count, Q
from django.utils import timezone
from skill_tracker.models import SkillResult
from routine_tracker.models import DailyRoutineAttempt
from .models import AthletePracticePlan, AthleteFeedback, PersonalMilestone
from .report_preferences import show_group_averages


def approved(query):
    return query.filter(Q(engagement_record__status='approved') |
        Q(engagement_record__isnull=True, recorded_by__role__in=['coach', 'head_coach'])).distinct()


def daily_counts(gym_id, athlete_id, when):
    skills = list(SkillResult.objects.filter(assignment__skill__gym_id=gym_id, assignment__athlete_id=athlete_id, practice_date=when)
        .values('assignment_id', 'result').annotate(total=Count('pk')))
    routines = list(DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, athlete_id=athlete_id, session__practice_date=when)
        .values('event', 'is_pressure', 'result').annotate(total=Count('pk')))
    return {'athlete': str(athlete_id), 'skills': skills, 'routines': routines,
            'as_of': timezone.now().isoformat()}


def refresh_milestones(gym_id, athlete_id, when):
    plan = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete_id=athlete_id, practice_date=when).first()
    if not plan:
        PersonalMilestone.objects.filter(gym_id=gym_id, athlete_id=athlete_id, practice_date=when, key__startswith='goal:').update(active=False)
        return []
    targets = []
    content = plan.content if isinstance(plan.content, dict) else {}
    for event, data in content.items():
        if not isinstance(data, dict): continue
        for item in data.get('skills', []):
            if not isinstance(item, dict): continue
            skill_id, goal = item.get('id'), item.get('target')
            if isinstance(goal, int) and goal > 0:
                total = approved(SkillResult.objects.filter(assignment__skill_id=skill_id, assignment__skill__gym_id=gym_id, assignment__athlete_id=athlete_id, practice_date=when)).count()
                targets.append((f'goal:{when}:skill:{skill_id}', goal, total, f"Practice target completed: {item.get('name', 'skill')}"))
        for key, pressure in [('routines', False), ('pressure', True)]:
            goal = data.get(key)
            if isinstance(goal, int) and goal > 0:
                total = approved(DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, session__practice_date=when, athlete_id=athlete_id, event=event, is_pressure=pressure)).count()
                targets.append((f'goal:{when}:{event}:{key}', goal, total, f"Practice target completed: {event.title()} {'pressure sets' if pressure else 'routines'}"))
    fresh, valid = [], []
    for key, goal, total, title in targets:
        if total < goal: continue
        valid.append(key)
        item, created = PersonalMilestone.objects.get_or_create(gym_id=gym_id, athlete_id=athlete_id, key=key,
            defaults={'title': title[:150], 'practice_date': when, 'details': {'target': goal}})
        if not item.active:
            item.active = True; item.save(update_fields=['active'])
        if created: fresh.append({'id': item.pk, 'title': item.title})
    PersonalMilestone.objects.filter(gym_id=gym_id, athlete_id=athlete_id, practice_date=when, key__startswith='goal:').exclude(key__in=valid).update(active=False)
    return fresh


def weekly_snapshot(coach, athlete, gym_id, week_start, allowed):
    end = week_start + timedelta(days=6)
    skills = approved(SkillResult.objects.filter(assignment__skill__gym_id=gym_id, assignment__athlete=athlete, practice_date__range=(week_start, end)))
    routines = approved(DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, athlete=athlete, session__practice_date__range=(week_start, end)))
    def rows(query, fields):
        grouped = defaultdict(lambda: {'wow': 0, 'hit': 0, 'missed': 0})
        for value in query.order_by().values(*fields, 'result').annotate(total=Count('pk')):
            grouped[tuple(value[field] for field in fields)][value['result']] = value['total']
        output = []
        for key, counts in grouped.items():
            total = sum(counts.values())
            output.append({'label': ' · '.join(str(x).title() if isinstance(x, str) else ('Pressure set' if x else 'Routine') for x in key),
                'wow': counts['wow'], 'hit': counts['hit'], 'attempt': counts['missed'], 'total': total,
                'success': round((counts['wow'] + counts['hit']) * 100 / total) if total else 0})
        return sorted(output, key=lambda row: row['label'])
    skill_rows = rows(skills, ['assignment__skill__event', 'assignment__skill__name'])
    routine_rows = rows(routines, ['event', 'is_pressure'])
    all_rows = skill_rows + routine_rows
    previous_start, previous_end = week_start - timedelta(days=7), week_start - timedelta(days=1)
    previous = approved(SkillResult.objects.filter(assignment__skill__gym_id=gym_id, assignment__athlete=athlete, practice_date__range=(previous_start, previous_end))).count()
    previous += approved(DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, athlete=athlete, session__practice_date__range=(previous_start, previous_end))).count()
    shared = list(AthleteFeedback.objects.filter(gym_id=gym_id, athlete=athlete, created_at__date__range=(week_start, end)).exclude(shared_feedback='').values_list('shared_feedback', flat=True))
    milestones = list(PersonalMilestone.objects.filter(gym_id=gym_id, athlete=athlete, active=True, practice_date__range=(week_start, end)).values_list('title', flat=True))
    result = {'skills': skill_rows, 'routines': routine_rows, 'total': sum(row['total'] for row in all_rows),
        'wow': sum(row['wow'] for row in all_rows), 'hit': sum(row['hit'] for row in all_rows),
        'attempt': sum(row['attempt'] for row in all_rows), 'previous_total': previous,
        'shared_feedback': shared, 'milestones': milestones, 'group': None}
    if show_group_averages(coach, gym_id):
        # Use exactly the coach's authorized roster, restricted to the child's assigned groups when possible.
        from gyms.models import TrainingGroupAthlete
        group_ids = TrainingGroupAthlete.objects.filter(athlete=athlete, is_active=True, group__gym_id=gym_id, group__is_active=True, group__coach_assignments__coach=coach).values('group_id')
        peers = allowed
        if group_ids.exists(): peers = peers.filter(training_groups__group_id__in=group_ids, training_groups__is_active=True).distinct()
        peer_ids = list(peers.values_list('pk', flat=True))
        group_counts = defaultdict(lambda: {'wow': 0, 'hit': 0, 'missed': 0})
        for query in [approved(SkillResult.objects.filter(assignment__skill__gym_id=gym_id, assignment__athlete_id__in=peer_ids, practice_date__range=(week_start, end))).values('assignment__athlete_id', 'result').annotate(total=Count('pk')),
                      approved(DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, athlete_id__in=peer_ids, session__practice_date__range=(week_start, end))).values('athlete_id', 'result').annotate(total=Count('pk'))]:
            for value in query:
                person = value.get('athlete_id', value.get('assignment__athlete_id'))
                group_counts[person][value['result']] += value['total']
        if group_counts:
            result['group'] = {key: round(sum(c[key] for c in group_counts.values()) / len(group_counts), 1) for key in ('wow', 'hit', 'missed')}
    return result
