import json
from datetime import date
from uuid import UUID
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from gyms.models import GymMembership
from practice_focus.access import coach_gym_id, gym_athletes
from practice_focus.models import EventSkillPlan, EVENTS
from .models import Skill, Assignment, SkillResult
from .services import normalize


def scope(request):
    user = request.user
    if user.role in ['coach', 'head_coach']:
        gym_id = coach_gym_id(user)
        athletes = gym_athletes(gym_id)
        selected = request.POST.get('athlete') if request.method == 'POST' else request.GET.get('athlete')
        if selected:
            try:
                athlete = get_object_or_404(athletes, pk=int(selected))
            except (ValueError, TypeError):
                raise PermissionDenied('Invalid athlete.')
        else:
            athlete = athletes.first()
        return gym_id, athletes, athlete, True
    if not user.is_active or user.role != 'athlete':
        raise PermissionDenied('Skill Tracker is available to active coaches and athletes.')
    gyms = list(GymMembership.objects.filter(user=user, role='athlete', is_active=True,
        gym__is_active=True).values_list('gym_id', flat=True).distinct()[:2])
    if len(gyms) != 1:
        raise PermissionDenied('A single active athlete gym is required.')
    return gyms[0], [], user, False


@login_required
@require_GET
def tracker(request):
    from .group_picker import tracker_page
    return tracker_page(request)


@login_required
@require_http_methods(['GET', 'POST'])
def manage(request):
    gym_id = coach_gym_id(request.user)
    athletes = gym_athletes(gym_id)
    selected = request.POST.get('athlete') if request.method == 'POST' else request.GET.get('athlete')
    try:
        athlete = get_object_or_404(athletes, pk=int(selected)) if selected else athletes.first()
    except (TypeError, ValueError):
        raise PermissionDenied('Invalid athlete.')
    error = ''
    posted_selection = None
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'catalogue':
                event = request.POST.get('event')
                if event not in dict(EVENTS):
                    raise ValidationError('Choose an event.')
                names = list(dict.fromkeys(normalize(n) for n in request.POST.get('names', '').splitlines() if normalize(n)))
                if not names or len(names) > 50 or any(len(n) > 150 for n in names):
                    raise ValidationError('Add 1–50 skills, one per line, with at most 150 characters each.')
                with transaction.atomic():
                    for name in names:
                        Skill.objects.get_or_create(gym_id=gym_id, event=event,
                            key=name.casefold(), defaults={'name': name})
                messages.success(request, 'Skills added to your gym’s list. Select an athlete to assign them.')
            elif request.POST.get('action') == 'assign':
                if not athlete or not selected:
                    raise ValidationError('Select an athlete first.')
                try:
                    ids = set(int(x) for x in request.POST.getlist('skills'))
                except ValueError:
                    raise ValidationError('Invalid skill selection.')
                posted_selection = ids
                skills = list(Skill.objects.filter(gym_id=gym_id, pk__in=ids))
                if len(skills) != len(ids):
                    raise ValidationError('Choose skills from your gym’s list.')
                with transaction.atomic():
                    get_user_model().objects.select_for_update().get(pk=athlete.pk)
                    plans = {p.event: p for p in EventSkillPlan.objects.select_for_update().filter(gym_id=gym_id, athlete=athlete)}
                    for event, label in EVENTS:
                        current = plans.get(event)
                        version = current.updated_at.isoformat() if current else ''
                        if request.POST.get('version_' + event, '') != version:
                            raise ValidationError('This athlete’s skills changed while you were editing. Reload the page before saving.')
                        names = [s.name for s in skills if s.event == event]
                        if len(names) > 50 or len('\n'.join(names)) > 8000:
                            raise ValidationError('Assign at most 50 skills per event.')
                        if not current and not names:
                            continue
                        plan = current or EventSkillPlan(gym_id=gym_id, athlete=athlete, event=event)
                        plan.skills_text = '\n'.join(names)
                        plan.updated_by = request.user
                        plan.full_clean()
                        plan.save()  # Signal synchronizes assignments; training cues are preserved.
                messages.success(request, 'Athlete skills saved and connected to the practice planner.')
            else:
                raise ValidationError('Invalid action.')
            return redirect(reverse('skill_tracker:manage') + (f'?athlete={athlete.pk}' if athlete else ''))
        except ValidationError as exc:
            error = ' '.join(exc.messages)
    active_ids = set(Assignment.objects.filter(athlete=athlete, skill__gym_id=gym_id,
        is_active=True).values_list('skill_id', flat=True)) if athlete else set()
    if posted_selection is not None:
        active_ids = posted_selection
    plans = {p.event: p for p in EventSkillPlan.objects.filter(gym_id=gym_id, athlete=athlete)} if athlete else {}
    skills = list(Skill.objects.filter(gym_id=gym_id))
    rows = [{'code': code, 'label': label, 'skills': [s for s in skills if s.event == code],
        'version': plans[code].updated_at.isoformat() if code in plans else ''} for code, label in EVENTS]
    return render(request, 'skill_tracker/manage.html', dict(athletes=athletes, athlete=athlete,
        rows=rows, active_ids=active_ids, error=error))


@login_required
@require_POST
def save_results(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or not all(key in payload for key in ['athlete', 'date', 'entries']):
            raise ValueError()
        # Resolve coach selection through the same membership checks as the page.
        request.POST = request.POST.copy()
        request.POST['athlete'] = str(payload.get('athlete', ''))
        gym_id, _, athlete, coach = scope(request)
        if athlete is None or str(payload.get('athlete')) != str(athlete.pk):
            raise PermissionDenied('Choose an authorized athlete.')
        practice_date = date.fromisoformat(payload['date'])
        if practice_date > timezone.localdate() or (not coach and practice_date != timezone.localdate()):
            raise ValueError()
        entries = payload['entries']
        if not isinstance(entries, list) or not 1 <= len(entries) <= 500:
            raise ValueError()
        parsed = []
        for entry in entries:
            if entry['result'] not in ['wow', 'hit', 'missed']:
                raise ValueError()
            parsed.append((int(entry['assignment']), entry['result'], UUID(entry['token'])))
        if len({token for _, _, token in parsed}) != len(parsed):
            raise ValueError()
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=athlete.pk)
            allowed = {a.pk: a for a in Assignment.objects.filter(athlete=athlete,
                skill__gym_id=gym_id, is_active=True)}
            for assignment_id, result, token in parsed:
                if assignment_id not in allowed:
                    raise ValidationError('A selected skill is no longer assigned. Reload the tracker before saving.')
                existing = SkillResult.objects.filter(token=token).first()
                if existing:
                    if (existing.assignment_id, existing.result, existing.practice_date, existing.recorded_by_id) != (assignment_id, result, practice_date, request.user.pk):
                        raise ValidationError('A result token has already been used.')
                else:
                    SkillResult.objects.create(assignment=allowed[assignment_id], result=result,
                        practice_date=practice_date, recorded_by=request.user, token=token)
        return JsonResponse({'ok': True, 'count': len(parsed)})
    except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid practice results or date.'}, status=400)
    except IntegrityError:
        return JsonResponse({'error': 'These results overlap another save. Retry the same practice.'}, status=400)
    except ValidationError as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=400)
