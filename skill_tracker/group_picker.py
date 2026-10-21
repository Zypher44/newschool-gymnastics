from collections import defaultdict

from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber
from django.shortcuts import render
from django.utils import timezone

from gyms.models import TrainingGroup, TrainingGroupAthlete
from practice_focus.models import EVENTS
from .models import Assignment, SkillResult


def tracker_page(request):
    # Reuse the existing page and save endpoint's authorization rules.
    from .views import scope

    gym_id, athletes, selected, coach = scope(request)
    people = list(athletes) if coach else [selected]
    people = [person for person in people if person is not None]
    ids = [person.pk for person in people]
    today = timezone.localdate()
    assignments = Assignment.objects.filter(
        skill__gym_id=gym_id, athlete_id__in=ids, is_active=True,
    ).select_related('skill').annotate(
        wow=Count('results', filter=Q(results__practice_date=today, results__result='wow')),
        hit=Count('results', filter=Q(results__practice_date=today, results__result='hit')),
        missed=Count('results', filter=Q(results__practice_date=today, results__result='missed')),
    ).order_by('skill__name', 'pk')
    # V3 skill attempt targets
    from .practice_targets import attach_practice_targets
    assignments = attach_practice_targets(assignments, gym_id, ids, today)
    by_athlete = defaultdict(list)
    for assignment in assignments:
        by_athlete[assignment.athlete_id].append(assignment)

    # Keep each athlete's most recent 30 results in one query.
    recent = SkillResult.objects.filter(
        assignment__athlete_id__in=ids, assignment__skill__gym_id=gym_id,
    ).select_related('assignment__skill').annotate(
        history_rank=Window(
            expression=RowNumber(),
            partition_by=[F('assignment__athlete_id')],
            order_by=[F('created_at').desc(), F('pk').desc()],
        ),
    ).filter(history_rank__lte=30).order_by('assignment__athlete_id', '-created_at', '-pk')
    history = defaultdict(list)
    for result in recent:
        history[result.assignment.athlete_id].append(result)
    panels = [
        {'athlete': person,
         'rows': [{'code': code, 'label': label,
                   'assignments': [assignment for assignment in by_athlete[person.pk]
                                   if assignment.skill.event == code]}
                  for code, label in EVENTS],
         'recent': history[person.pk]}
        for person in people
    ]
    groups = []
    if coach:
        groups = list(TrainingGroup.objects.filter(gym_id=gym_id, is_active=True)
                      .order_by('name', 'pk').values('id', 'name'))
        members = {group['id']: [] for group in groups}
        for group_id, athlete_id in TrainingGroupAthlete.objects.filter(
            group_id__in=members, athlete_id__in=ids, is_active=True,
        ).values_list('group_id', 'athlete_id').distinct():
            members[group_id].append(str(athlete_id))
        groups = [{'id': str(group['id']), 'name': group['name'],
                   'athlete_ids': members[group['id']]} for group in groups]
    selected_panel = next((panel for panel in panels if selected and panel['athlete'].pk == selected.pk), None)
    return render(request, 'skill_tracker/tracker.html', {
        'athletes': people if coach else [], 'athlete': selected, 'coach': coach,
        'rows': selected_panel['rows'] if selected_panel else [],
        'recent': selected_panel['recent'] if selected_panel else [],
        'athlete_panels': panels, 'training_groups': groups,
        'gym_id': gym_id, 'today': today,
        'requested_athlete_id': str(selected.pk) if coach and selected and request.GET.get('athlete') else '',
    })
