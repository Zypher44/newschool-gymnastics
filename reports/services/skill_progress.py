from collections import defaultdict

from django.db.models import Count

from gyms.models import TrainingGroupAthlete
from practice_focus.models import EVENTS
from skill_tracker.models import SkillResult


def skill_comparison_data(user, athlete, allowed_athletes, gym_id, start_date, end_date):
    """Use the report's authorized roster and gym; count only saved results."""
    empty = {'rows': [], 'attempts': 0, 'wows': 0, 'hits': 0,
             'attempt_only': 0, 'success_rate': 0, 'scope_label': 'allowed athletes'}
    from practice_focus.report_preferences import report_gym_id
    if not gym_id or report_gym_id(user) != gym_id:
        return empty
    peer_ids = set(allowed_athletes.filter(
        is_active=True, role='athlete',
        gym_memberships__gym_id=gym_id,
        gym_memberships__role='athlete', gym_memberships__is_active=True,
    ).values_list('pk', flat=True))
    if athlete.pk not in peer_ids:
        return empty

    from practice_focus.report_preferences import show_group_averages
    include_group_averages = show_group_averages(user, gym_id)
    if include_group_averages:
        group_ids = list(TrainingGroupAthlete.objects.filter(
            athlete=athlete, is_active=True,
            group__gym_id=gym_id, group__is_active=True,
            group__coach_assignments__coach=user,
        ).values_list('group_id', flat=True).distinct())
        if group_ids:
            group_peer_ids = set(TrainingGroupAthlete.objects.filter(
                group_id__in=group_ids, group__gym_id=gym_id,
                is_active=True, athlete__is_active=True,
            ).values_list('athlete_id', flat=True))
            peer_ids &= group_peer_ids
            empty['scope_label'] = 'assigned training group'
    else:
        peer_ids = {athlete.pk}

    aggregates = SkillResult.objects.filter(
        assignment__skill__gym_id=gym_id,
        assignment__athlete_id__in=peer_ids,
        practice_date__range=(start_date, end_date),
    ).order_by().values(
        'assignment__skill_id', 'assignment__skill__event',
        'assignment__skill__name', 'assignment__athlete_id', 'result',
    ).annotate(total=Count('pk'))
    skills = {}
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for item in aggregates:
        skill_id = item['assignment__skill_id']
        skills[skill_id] = (item['assignment__skill__event'], item['assignment__skill__name'])
        counts[skill_id][item['assignment__athlete_id']][item['result']] += item['total']

    event_labels = dict(EVENTS)
    event_order = {code: index for index, (code, label) in enumerate(EVENTS)}
    for skill_id in sorted(skills, key=lambda key: (
        event_order.get(skills[key][0], len(event_order)), skills[key][1].casefold(), key,
    )):
        event, name = skills[skill_id]
        child = {result: counts[skill_id][athlete.pk].get(result, 0)
                 for result in ('wow', 'hit', 'missed')}
        active_peers = [values for values in counts[skill_id].values() if sum(values.values())]
        totals = {result: sum(values.get(result, 0) for values in active_peers)
                  for result in ('wow', 'hit', 'missed')}
        child_total = sum(child.values())
        group_total = sum(totals.values())
        empty['rows'].append({
            'event': event_labels.get(event, event), 'skill': name,
            'athlete_counts': child, 'athlete_total': child_total,
            'athlete_success_rate': round((child['wow'] + child['hit']) * 100 / child_total) if child_total else None,
            'group_average': {result: round(totals[result] / len(active_peers), 1)
                              for result in totals},
            'group_success_rate': round((totals['wow'] + totals['hit']) * 100 / group_total) if group_total else None,
            'group_athletes': len(active_peers),
        })
        empty['attempts'] += child_total
        empty['wows'] += child['wow']
        empty['hits'] += child['hit']
        empty['attempt_only'] += child['missed']
    # V3 coach report preferences
    if not include_group_averages:
        empty['scope_label'] = ''
        for row in empty['rows']:
            for key in ('group_average', 'group_success_rate', 'group_athletes'):
                row.pop(key, None)
    if empty['attempts']:
        empty['success_rate'] = round((empty['wows'] + empty['hits']) * 100 / empty['attempts'])
    return empty
