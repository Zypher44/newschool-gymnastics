from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from gyms.models import TrainingGroup
from .access import coach_gym_id, gym_athletes
from .forms import EventSkillsForm
from .models import EventSkillPlan, EVENTS


def selected_id(value):
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        raise Http404('Invalid selection.')


@login_required
@require_http_methods(['GET', 'POST'])
def planner(request):
    gym_id = coach_gym_id(request.user)
    groups = TrainingGroup.objects.filter(gym_id=gym_id, is_active=True).order_by('name')
    source = request.POST if request.method == 'POST' else request.GET
    group_id = selected_id(source.get('group'))
    group = get_object_or_404(groups, pk=group_id) if group_id is not None else None
    athletes = gym_athletes(gym_id)
    if group is not None:
        athletes = athletes.filter(training_groups__group=group, training_groups__is_active=True).distinct()
    athlete_id = selected_id(source.get('athlete'))
    athlete = get_object_or_404(athletes, pk=athlete_id) if athlete_id is not None else athletes.first()
    if request.method == 'POST' and athlete_id is None:
        raise Http404('Choose an athlete before saving.')
    existing = {plan.event: plan for plan in EventSkillPlan.objects.filter(gym_id=gym_id, athlete=athlete)} if athlete else {}
    event_forms = []
    for code, label in EVENTS:
        plan = existing.get(code)
        initial = {'skills_text': plan.skills_text if plan else '', 'training_cues': plan.training_cues if plan else '',
                   'version': plan.updated_at.isoformat() if plan else ''}
        form = EventSkillsForm(request.POST if request.method == 'POST' else None, prefix=code, initial=initial)
        event_forms.append({'code': code, 'label': label, 'form': form})
    if request.method == 'POST':
        valid = [item['form'].is_valid() for item in event_forms]
        if all(valid):
            with transaction.atomic():
                # Serialize edits for this athlete, including first-time event records.
                type(athlete).objects.select_for_update().get(pk=athlete.pk)
                locked = {plan.event: plan for plan in EventSkillPlan.objects.select_for_update().filter(gym_id=gym_id, athlete=athlete)}
                stale = False
                for item in event_forms:
                    plan = locked.get(item['code'])
                    version = plan.updated_at.isoformat() if plan else ''
                    if version != item['form'].cleaned_data['version']:
                        item['form'].add_error(None, 'Another coach updated these skills. Reload before saving; your changes have not been saved.')
                        stale = True
                if not stale:
                    plans = []
                    for item in event_forms:
                        data = item['form'].cleaned_data
                        plan = locked.get(item['code'])
                        if not plan and not data['skills_text'] and not data['training_cues']:
                            continue
                        plan = plan or EventSkillPlan(gym_id=gym_id, athlete=athlete, event=item['code'])
                        plan.skills_text = data['skills_text']
                        plan.training_cues = data['training_cues']
                        plan.updated_by = request.user
                        try:
                            plan.full_clean()
                        except ValidationError as exc:
                            item['form'].add_error(None, '; '.join(exc.messages))
                        plans.append(plan)
                    if not any(item['form'].errors for item in event_forms):
                        for plan in plans:
                            plan.save()
                        messages.success(request, 'Current skills saved for all four events.')
                        query = {'athlete': athlete.pk}
                        if group:
                            query['group'] = group.pk
                        return redirect(reverse('practice_focus:planner') + '?' + urlencode(query))
    return render(request, 'practice_focus/planner.html', {
        'groups': groups, 'selected_group': group, 'athletes': athletes,
        'selected_athlete': athlete, 'event_forms': event_forms,
    })
