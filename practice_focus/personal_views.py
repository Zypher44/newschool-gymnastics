from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET
from gyms.models import GymMembership, TrainingGroup
from skill_tracker.models import Skill
from .access import coach_gym_id, gym_athletes
from .models import EVENTS
from .personal_models import AthletePracticePlan, PracticePlanTemplate
from .personal_forms import PersonalPlanForm
from .personal_services import current_values, current_version, snapshot, form_initial, sync_current_skills, progress_rows


def selection(value):
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        raise Http404('Invalid selection.')


def practice_day(value):
    try:
        return date.fromisoformat(value) if value else timezone.localdate()
    except (ValueError, TypeError):
        raise Http404('Choose a valid practice date.')


@login_required
@require_http_methods(['GET', 'POST'])
def planner(request):
    if request.user.role == 'athlete':
        return redirect('practice_focus:my_plan')
    gym_id = coach_gym_id(request.user)
    source = request.POST if request.method == 'POST' else request.GET
    day = practice_day(source.get('date'))
    groups = TrainingGroup.objects.filter(gym_id=gym_id, is_active=True).order_by('name')
    group_id = selection(source.get('group'))
    group = get_object_or_404(groups, pk=group_id) if group_id is not None else None
    athletes = gym_athletes(gym_id)
    if group:
        athletes = athletes.filter(training_groups__group=group, training_groups__is_active=True).distinct()
    athlete_id = selection(source.get('athlete'))
    athlete = get_object_or_404(athletes, pk=athlete_id) if athlete_id is not None else athletes.first()
    if request.method == 'POST' and athlete_id is None:
        raise Http404('Choose an athlete first.')
    skills = list(Skill.objects.filter(gym_id=gym_id).order_by('name', 'pk'))
    templates = PracticePlanTemplate.objects.filter(gym_id=gym_id)
    plan = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete=athlete, practice_date=day).first() if athlete else None
    values = {'title': plan.title, **snapshot(plan)} if plan else current_values(gym_id, athlete, skills) if athlete else {'title': 'Daily practice'}
    version = plan.updated_at.isoformat() if plan else ''
    tracker_version = current_version(gym_id, athlete) if athlete else ''
    initial = form_initial(values, version, tracker_version, skills)
    form = PersonalPlanForm(skills=skills, initial=initial)
    draft = False
    action = source.get('action') if request.method == 'POST' else None
    if action in ('load_template', 'copy'):
        if action == 'load_template':
            template = get_object_or_404(templates, pk=selection(source.get('template')))
            values = {'title': template.name, **snapshot(template)}
        else:
            copy_date = practice_day(source.get('copy_date'))
            original = get_object_or_404(AthletePracticePlan, gym_id=gym_id, athlete=athlete, practice_date=copy_date)
            values = {'title': original.title, **snapshot(original)}
        form = PersonalPlanForm(skills=skills, initial=form_initial(values, version, tracker_version, skills))
        draft = True
    elif request.method == 'POST':
        form = PersonalPlanForm(request.POST, skills=skills)
        if action not in ('save', 'publish', 'template'):
            form.add_error(None, 'Choose a valid action.')
        elif form.is_valid():
            values = form.plan_values()
            try:
                with transaction.atomic():
                    get_user_model().objects.select_for_update().get(pk=athlete.pk)
                    locked = AthletePracticePlan.objects.select_for_update().filter(gym_id=gym_id, athlete=athlete, practice_date=day).first()
                    if form.cleaned_data['version'] != (locked.updated_at.isoformat() if locked else ''):
                        raise ValidationError('Another coach changed this athlete’s plan. Reload before saving. Your changes have not been saved.')
                    if action == 'template':
                        name = ' '.join(source.get('template_name', '').split())
                        if not name or len(name) > 150 or len(name.casefold()) > 150:
                            raise ValidationError('Give the template a name of 1–150 characters.')
                        PracticePlanTemplate.objects.create(gym_id=gym_id, name=name, key=name.casefold(),
                            created_by=request.user, **{key: values[key] for key in ['level', 'focus', 'notes', 'content']})
                    else:
                        if action == 'publish':
                            if day != timezone.localdate():
                                raise ValidationError('Use today’s plan to set current tracker skills. Future and past plans can be saved without changing the trackers.')
                            if form.cleaned_data['current_version'] != current_version(gym_id, athlete):
                                raise ValidationError('Current tracker skills changed while you were editing. Reload before setting current skills.')
                        locked = locked or AthletePracticePlan(gym_id=gym_id, athlete=athlete, practice_date=day)
                        for field, value in values.items():
                            setattr(locked, field, value)
                        locked.updated_by = request.user
                        locked.full_clean()
                        locked.save()
                        if action == 'publish':
                            sync_current_skills(gym_id, athlete, request.user, values)
                if action == 'template':
                    messages.success(request, 'Reusable template saved. Save this athlete’s plan separately when you are ready.')
                    templates = PracticePlanTemplate.objects.filter(gym_id=gym_id)
                    draft = True
                else:
                    messages.success(request, 'Athlete plan saved.' + (' Current skills updated in both trackers.' if action == 'publish' else ''))
                    query = {'athlete': athlete.pk, 'date': day.isoformat()}
                    if group:
                        query['group'] = group.pk
                    return redirect(reverse('practice_focus:planner') + '?' + urlencode(query))
            except IntegrityError:
                form.add_error(None, 'A template with that name already exists. Choose a different name.')
            except ValidationError as error:
                form.add_error(None, ' '.join(error.messages))
    event_forms = []
    for event, label in EVENTS:
        event_forms.append({'code': event, 'label': label,
            'minutes': form[event + '_minutes'], 'routines': form[event + '_routines'],
            'pressure': form[event + '_pressure'], 'cue': form[event + '_cue'],
            'skills': [{'skill': skill, 'check': form['skill_' + str(skill.pk)], 'target': form['target_' + str(skill.pk)]}
                       for skill in skills if skill.event == event]})
    return render(request, 'practice_focus/personal_planner.html', {
        'groups': groups, 'selected_group': group, 'athletes': athletes, 'selected_athlete': athlete,
        'day': day, 'today': timezone.localdate(), 'form': form, 'event_forms': event_forms,
        'templates': templates, 'saved_plan': plan, 'draft': draft, 'progress': progress_rows(plan),
        'copy_plans': AthletePracticePlan.objects.filter(gym_id=gym_id, athlete=athlete).exclude(practice_date=day)[:60] if athlete else [],
        'template_name': source.get('template_name', '') if request.method == 'POST' else '',
    })


@login_required
@require_GET
def my_plan(request):
    user = request.user
    if not user.is_active or user.role != 'athlete':
        raise PermissionDenied('This page is for active athletes.')
    gyms = list(GymMembership.objects.filter(user=user, role='athlete', is_active=True,
        gym__is_active=True).values_list('gym_id', flat=True).distinct()[:2])
    if len(gyms) != 1:
        raise PermissionDenied('A single active athlete gym is required.')
    day = practice_day(request.GET.get('date'))
    plan = AthletePracticePlan.objects.filter(gym_id=gyms[0], athlete=user, practice_date=day).first()
    return render(request, 'practice_focus/my_plan.html', {
        'plan': plan, 'day': day, 'today': timezone.localdate(), 'progress': progress_rows(plan),
    })
