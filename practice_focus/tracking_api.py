import json
from datetime import date
from uuid import UUID
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from skill_tracker.models import Assignment, SkillResult
from routine_tracker.models import DailyRoutineSession, DailyRoutineAttempt
from .models import TrackerMutation, TrackedResult
from .engagement_access import tracker_roster
from .engagement_services import daily_counts, refresh_milestones


def valid_date(value):
    when = date.fromisoformat(value)
    if when > timezone.localdate(): raise ValueError('Future practices cannot be scored.')
    return when


def serialize(record):
    return {'token': str(record.token), 'athlete': str(record.athlete_id), 'kind': record.kind,
        'date': record.practice_date.isoformat(), 'status': record.status, 'details': record.details,
        'source_id': record.skill_result_id or record.routine_result_id,
        'created_at': record.created_at.isoformat()}


@login_required
@never_cache
@require_GET
def tracker_state(request):
    gym_id, athletes = tracker_roster(request.user)
    try: when = valid_date(request.GET.get('date', timezone.localdate().isoformat()))
    except (ValueError, TypeError): return JsonResponse({'ok': False, 'error': 'Invalid practice date.'}, status=400)
    # Only the authorized roster is returned; GET cannot widen an athlete's scope.
    ids = list(athletes.values_list('pk', flat=True))
    records = TrackedResult.objects.filter(gym_id=gym_id, actor=request.user, practice_date=when, athlete_id__in=ids).order_by('-created_at')[:100]
    return JsonResponse({'ok': True, 'counts': [daily_counts(gym_id, pk, when) for pk in ids], 'recent': [serialize(r) for r in records]})


@login_required
@never_cache
@require_POST
def tracker_mutate(request):
    gym_id, athletes = tracker_roster(request.user)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict): raise ValueError('Invalid result.')
        token = UUID(payload['token'])
        removed_id = None
        action = payload.get('action', 'add')
        if action not in ('add', 'undo', 'remove'): raise ValueError('Invalid action.')
        with transaction.atomic():
            # Serialize retries from this account before reading the unique operation token.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            mutation = TrackerMutation.objects.filter(token=token).first()
            if mutation:
                if mutation.actor_id != request.user.pk or mutation.gym_id != gym_id or mutation.payload != payload:
                    raise PermissionDenied('That save token belongs to another operation.')
                response = dict(mutation.response)
                if response.get('counts'):
                    athlete_id = response['counts']['athlete']
                    get_object_or_404(athletes, pk=athlete_id)
                    response['counts'] = daily_counts(gym_id, athlete_id, valid_date(payload['date']))
                if response.get('record'):
                    current = get_object_or_404(TrackedResult.objects.filter(gym_id=gym_id, athlete__in=athletes), token=response['record']['token'])
                    response['record'] = serialize(current)
                return JsonResponse(response)
            if action == 'add':
                athlete = get_object_or_404(athletes, pk=int(payload['athlete']))
                when = valid_date(payload['date'])
                if request.user.role == 'athlete' and when != timezone.localdate():
                    raise ValueError('Athletes can add results for today only.')
                result = payload['result']; kind = payload['kind']
                if result not in ('wow', 'hit', 'missed'): raise ValueError('Choose Wow, Hit, or Attempt.')
                details = {'result': result}
                status = 'pending' if request.user.role == 'athlete' else 'approved'
                record = TrackedResult(gym_id=gym_id, athlete=athlete, actor=request.user, token=token,
                    practice_date=when, kind=kind, status=status)
                if kind == 'skill':
                    assignment = get_object_or_404(Assignment.objects.select_related('skill').filter(athlete=athlete, skill__gym_id=gym_id, is_active=True), pk=int(payload['assignment']))
                    details.update(assignment=assignment.pk, event=assignment.skill.event, label=assignment.skill.name)
                    record.skill_result = SkillResult.objects.create(assignment=assignment, result=result, practice_date=when, recorded_by=request.user, token=token)
                elif kind == 'routine':
                    if payload.get('event') not in dict(DailyRoutineAttempt.EVENT_CHOICES) or not isinstance(payload.get('pressure', False), bool):
                        raise ValueError('Choose a valid event and routine type.')
                    if payload.get('inline') is True and 'session' not in payload:
                        # The practice page stays read-only until the first routine result is tapped.
                        # Unique gym/date plus get_or_create handles simultaneous first taps safely.
                        session, _ = DailyRoutineSession.objects.get_or_create(gym_id=gym_id,
                            practice_date=when, defaults={'created_by': request.user})
                        session = DailyRoutineSession.objects.select_for_update().get(pk=session.pk)
                    else:
                        session = get_object_or_404(DailyRoutineSession.objects.select_for_update().filter(gym_id=gym_id, practice_date=when), pk=int(payload['session']))
                    pressure = payload.get('pressure', False)
                    number = DailyRoutineAttempt.objects.filter(session=session, athlete=athlete, event=payload['event'], is_pressure=pressure).aggregate(value=Max('attempt_number'))['value'] or 0
                    record.routine_result = DailyRoutineAttempt.objects.create(session=session, athlete=athlete, event=payload['event'], is_pressure=pressure,
                        attempt_number=number + 1, result=result, recorded_by=request.user)
                    details.update(event=payload['event'], pressure=pressure, label=f"{payload['event'].title()} {'pressure set' if pressure else 'routine'}")
                else: raise ValueError('Invalid tracker.')
                record.details = details; record.save()
            elif action == 'undo':
                record = get_object_or_404(TrackedResult.objects.select_for_update().filter(gym_id=gym_id, athlete__in=athletes, actor=request.user), token=UUID(payload['target']))
                removed_id = record.skill_result_id or record.routine_result_id
                if record.status not in ('undone', 'rejected'):
                    if record.skill_result_id: record.skill_result.delete()
                    if record.routine_result_id: record.routine_result.delete()
                    record.skill_result = None; record.routine_result = None; record.status = 'undone'
                    record.save(update_fields=['skill_result', 'routine_result', 'status'])
            else:
                if request.user.role not in ('coach', 'head_coach'): raise PermissionDenied('Coach access required.')
                attempt = DailyRoutineAttempt.objects.filter(session__gym_id=gym_id, athlete__in=athletes, pk=int(payload['source_id'])).first()
                if attempt is None:
                    # A retried removal uses its mutation token. A different already-removed ID is harmless.
                    response = {'ok': True, 'removed': True, 'milestones': []}
                    TrackerMutation.objects.create(token=token, gym_id=gym_id, actor=request.user, payload=payload, response=response)
                    return JsonResponse(response)
                when, athlete = attempt.session.practice_date, attempt.athlete
                existing = TrackedResult.objects.select_for_update().filter(routine_result=attempt).first()
                if existing:
                    existing.status = 'undone'; existing.routine_result = None; existing.save(update_fields=['status', 'routine_result'])
                attempt.delete()
                fresh = refresh_milestones(gym_id, athlete.pk, when)
                response = {'ok': True, 'removed': True, 'counts': daily_counts(gym_id, athlete.pk, when), 'milestones': fresh}
                TrackerMutation.objects.create(token=token, gym_id=gym_id, actor=request.user, payload=payload, response=response)
                return JsonResponse(response)
            fresh = refresh_milestones(gym_id, record.athlete_id, record.practice_date)
            response = {'ok': True, 'removed_id': removed_id, 'record': serialize(record), 'counts': daily_counts(gym_id, record.athlete_id, record.practice_date), 'milestones': fresh}
            TrackerMutation.objects.create(token=token, gym_id=gym_id, actor=request.user, payload=payload, response=response)
        return JsonResponse(response)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return JsonResponse({'ok': False, 'error': str(error) if str(error) else 'Invalid practice result.'}, status=400)
    except (ValidationError, IntegrityError):
        return JsonResponse({'ok': False, 'error': 'This result could not be saved. Retry the same result.'}, status=409)
