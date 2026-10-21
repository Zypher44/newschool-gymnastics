from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from athletes.models import AttendanceRecord
from practice_focus.models import EVENTS, AthletePracticePlan
from .access import practice_scope, group_roster
from .models import PracticeSession, AthletePracticeTimer
from .services import athlete_rows, link, positive
from .timers import group_deadline, stop_group, start_group, clock_values, remaining


def identifier(value):
    try:
        number = int(value)
        if number < 1:
            raise ValueError
        return number
    except (ValueError, TypeError):
        raise Http404('Choose a valid group or athlete.')


def child_timer_defaults(plan):
    """Initial settings belong to the child's own plan, never the open tracker event."""
    content = plan.content if plan and isinstance(plan.content, dict) else {}
    for code, _ in EVENTS:
        details = content.get(code, {})
        if isinstance(details, dict) and any(details.get(key) for key in ('skills', 'minutes', 'routines', 'pressure', 'cue')):
            return code, max(1, min(120, positive(details.get('minutes')) or 15))
    return 'floor', 15


def mark_unrecorded_present(roster, today, coach):
    count = 0
    for person in roster.order_by('pk'):
        get_user_model().objects.select_for_update().get(pk=person.pk)
        _, created = AttendanceRecord.objects.get_or_create(athlete=person,
            attendance_date=today, defaults={'coach': coach, 'status': 'present'})
        count += int(created)
    return count


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def start_practice(request):
    gym_id, athletes, groups = practice_scope(request.user)
    today = timezone.localdate()
    source = request.POST if request.method == 'POST' else request.GET
    group_id = source.get('group')
    recent = PracticeSession.objects.filter(gym_id=gym_id, coach=request.user,
        practice_date=today, group__in=groups, finished_at__isnull=True).first()
    group = get_object_or_404(groups, pk=identifier(group_id)) if group_id else (
        recent.group if recent else groups.first() if groups.count() == 1 else None)
    roster = group_roster(athletes, group) if group else athletes.none()
    session = PracticeSession.objects.filter(gym_id=gym_id, coach=request.user,
        group=group, practice_date=today).first() if group else None
    event = source.get('event') or (session.event if session else 'floor')
    if event not in dict(EVENTS):
        return HttpResponseBadRequest('Choose a valid event.')
    selected_id = identifier(source.get('athlete')) if source.get('athlete') else None
    if selected_id is not None:
        get_object_or_404(roster, pk=selected_id)
        if request.method == 'GET' and not (session and session.finished_at):
            # The selected child's persisted event is the active event for both trackers.
            selected_timer = AthletePracticeTimer.objects.filter(session=session, athlete_id=selected_id).first() if session else None
            selected_plan = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete_id=selected_id, practice_date=today).first() if not selected_timer else None
            event = selected_timer.event if selected_timer else child_timer_defaults(selected_plan)[0]
    if request.method == 'POST':
        if not group:
            return HttpResponseBadRequest('Choose a training group first.')
        action = source.get('action')
        if action not in ('start', 'open_skill', 'open_routine', 'quick_present', 'reopen', 'rotate', 'timer', 'group_start', 'group_stop', 'group_extend', 'child_start', 'child_stop', 'child_configure', 'child_event', 'finish', 'present', 'attendance'):
            return HttpResponseBadRequest('Choose a valid practice action.')
        if action in ('open_skill', 'open_routine') and selected_id is None:
            return HttpResponseBadRequest('Tap an athlete’s name first.')
        if not roster.exists():
            return HttpResponseBadRequest('This group has no athletes you can coach.')
        try:
            version = int(source.get('version', '0'))
            minutes = int(source.get('minutes', session.rotation_minutes if session else 15))
            if not 1 <= minutes <= 120:
                raise ValueError
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Choose a rotation of 1–120 minutes.')
        if action == 'group_extend':
            try:
                extra_minutes = int(source.get('extra_minutes', ''))
                if extra_minutes not in (1, 5):
                    raise ValueError
            except (ValueError, TypeError):
                return HttpResponseBadRequest('Choose +1 or +5 minutes.')
        try:
            with transaction.atomic():
                # Serialize starts and retries for the same coach, including new sessions.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                session = PracticeSession.objects.select_for_update().filter(gym_id=gym_id,
                    coach=request.user, group=group, practice_date=today).first()
                if action == 'group_extend':
                    if session and session.finished_at:
                        raise ValidationError('Resume practice before extending the group timer.')
                    if version != (session.version if session else 0):
                        raise ValidationError('This timer changed in another tab. Try again using the updated timer.')
                    now = timezone.now()
                    if not session:
                        session = PracticeSession.objects.create(gym_id=gym_id, coach=request.user,
                            group=group, practice_date=today, event=event, rotation_minutes=minutes,
                            rotation_started_at=now, started_at=now, rotation_paused_seconds=minutes * 60)
                    paused = session.rotation_paused_seconds is not None
                    seconds = session.rotation_paused_seconds if paused else remaining(group_deadline(session), now)
                    seconds += extra_minutes * 60
                    if seconds > 120 * 60:
                        raise ValidationError('The group timer can have up to 120 minutes remaining.')
                    if paused:
                        session.rotation_paused_seconds = seconds
                    else:
                        session.rotation_deadline = max(group_deadline(session), now) + timedelta(minutes=extra_minutes)
                    session.version += 1
                    session.save(update_fields=['rotation_deadline', 'rotation_paused_seconds', 'version'])
                elif action in ('start', 'open_skill', 'open_routine', 'quick_present', 'group_start', 'child_start', 'child_configure', 'child_event'):
                    if session and session.finished_at:
                        raise ValidationError('This practice has finished. Open Practice tools and resume it to keep recording.')
                    if not session:
                        if version != 0:
                            raise ValidationError('The practice changed. Reload before starting.')
                        now = timezone.now()
                        session = PracticeSession.objects.create(gym_id=gym_id, coach=request.user,
                            group=group, practice_date=today, event=event, rotation_minutes=minutes,
                            rotation_started_at=now, started_at=now,
                            rotation_paused_seconds=minutes * 60 if action in ('child_configure', 'child_event') else None)
                    # A repeated start resumes the existing session without resetting its timer.
                    if action == 'quick_present':
                        count = mark_unrecorded_present(roster, today, request.user)
                        messages.success(request, f'{count} unrecorded athlete(s) marked present. Existing attendance was kept.')
                    if action == 'group_start' and session.rotation_paused_seconds is not None:
                        if version != session.version:
                            raise ValidationError('This timer changed in another tab. Try again using the updated timer.')
                        start_group(session, timezone.now())
                        session.version += 1
                        session.save(update_fields=['rotation_deadline', 'rotation_paused_seconds', 'version'])
                else:
                    if not session:
                        raise ValidationError('Start this practice first.')
                    if action == 'reopen':
                        if version != session.version:
                            raise ValidationError('This practice changed. Reload before reopening it.')
                        if session.finished_at:
                            session.finished_at = None
                            session.rotation_started_at = timezone.now()
                            session.rotation_deadline = None
                            session.rotation_paused_seconds = None
                            session.version += 1
                            session.save(update_fields=['finished_at', 'rotation_started_at', 'rotation_deadline', 'rotation_paused_seconds', 'version'])
                    elif action == 'finish' and session.finished_at:
                        pass  # Finishing twice does not change the existing finish time.
                    elif session.finished_at:
                        raise ValidationError('This practice has finished. Open the attendance page to make later corrections.')
                    elif version != session.version:
                        raise ValidationError('This practice changed in another tab. Reload before making this change.')
                    elif action in ('rotate', 'timer'):
                        session.event = event
                        session.rotation_minutes = minutes
                        session.rotation_started_at = timezone.now()
                        session.rotation_deadline = None
                        session.rotation_paused_seconds = None
                        session.version += 1
                        session.save(update_fields=['event', 'rotation_minutes', 'rotation_started_at', 'rotation_deadline', 'rotation_paused_seconds', 'version'])
                    elif action == 'group_stop':
                        stop_group(session, timezone.now())
                        session.version += 1
                        session.save(update_fields=['rotation_paused_seconds', 'version'])
                    elif action == 'finish':
                        session.finished_at = timezone.now()
                        stop_group(session, session.finished_at)
                        for timer in session.athlete_timers.select_for_update().filter(deadline__isnull=False):
                            timer.remaining_seconds = remaining(timer.deadline, session.finished_at)
                            timer.deadline = None
                            timer.version += 1
                            timer.save(update_fields=['remaining_seconds', 'deadline', 'version'])
                        session.version += 1
                        session.save(update_fields=['finished_at', 'rotation_paused_seconds', 'version'])
                    elif action == 'present':
                        count = mark_unrecorded_present(roster, today, request.user)
                        messages.success(request, f'{count} unrecorded athlete(s) marked present. Existing attendance was kept.')
                    elif action == 'attendance':
                        person = get_object_or_404(roster, pk=identifier(source.get('attendance_athlete')))
                        status = source.get('status')
                        if status not in dict(AttendanceRecord.STATUS_CHOICES):
                            return HttpResponseBadRequest('Choose a valid attendance status.')
                        get_user_model().objects.select_for_update().get(pk=person.pk)
                        record = AttendanceRecord.objects.select_for_update().filter(athlete=person,
                            attendance_date=today).first()
                        if source.get('attendance_version', '') != (record.updated_at.isoformat() if record else ''):
                            raise ValidationError('This athlete’s attendance changed. Reload before saving.')
                        record = record or AttendanceRecord(athlete=person, attendance_date=today)
                        record.status = status
                        record.coach = request.user
                        record.save()  # Preserve existing attendance notes.
                if action in ('child_start', 'child_stop', 'child_configure', 'child_event'):
                    person = get_object_or_404(roster, pk=identifier(source.get('timer_athlete')))
                    timer = AthletePracticeTimer.objects.select_for_update().filter(session=session, athlete=person).first()
                    plan = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete=person, practice_date=today).first() if not timer else None
                    default_event, default_minutes = child_timer_defaults(plan)
                    try:
                        timer_version = int(source.get('timer_version', '0'))
                        timer_minutes = (timer.minutes if timer else default_minutes) if action == 'child_event' else int(source.get('timer_minutes', timer.minutes if timer else default_minutes))
                        timer_event = source.get('timer_event', timer.event if timer else default_event)
                        if not 1 <= timer_minutes <= 120 or timer_event not in dict(EVENTS):
                            raise ValueError
                    except (TypeError, ValueError):
                        raise ValidationError('Choose a valid child event and 1–120 minutes.')
                    if timer_version != (timer.version if timer else 0):
                        raise ValidationError('This child’s timer changed in another tab. Try again using the updated timer.')
                    now = timezone.now()
                    timer = timer or AthletePracticeTimer(session=session, athlete=person, event=timer_event,
                        minutes=timer_minutes, remaining_seconds=timer_minutes * 60, version=0)
                    if action == 'child_event':
                        # Event selection changes only the label, keeping elapsed time and run/pause state.
                        timer.event = timer_event
                        if selected_id == person.pk:
                            event = timer_event
                    elif action == 'child_configure':
                        if timer.deadline:
                            raise ValidationError('Stop this child’s timer before changing its event or duration.')
                        if timer.event != timer_event or timer.minutes != timer_minutes:
                            timer.remaining_seconds = timer_minutes * 60
                        timer.event, timer.minutes = timer_event, timer_minutes
                    elif action == 'child_stop' and timer.deadline:
                        timer.remaining_seconds = remaining(timer.deadline, now)
                        timer.deadline = None
                    elif action == 'child_start' and not timer.deadline:
                        if timer.event != timer_event or timer.minutes != timer_minutes or not timer.remaining_seconds:
                            timer.remaining_seconds = timer_minutes * 60
                        timer.event, timer.minutes = timer_event, timer_minutes
                        timer.deadline = now + timedelta(seconds=timer.remaining_seconds)
                    timer.version += 1
                    timer.save()
                if action == 'finish':
                    messages.success(request, 'Practice finished. Review athlete results and choose which feedback to share.')
            if action in ('open_skill', 'open_routine'):
                name = 'skill_tracker:tracker' if action == 'open_skill' else 'routine_tracker:daily_routine_tracker'
                return redirect(link(name, group=group.pk, athlete=selected_id,
                    event=event, practice_session=session.pk))
            return redirect(link('practice_hub:start', group=group.pk,
                athlete=selected_id, event=event,
                tools=1 if action in ('start', 'reopen', 'timer', 'present', 'attendance', 'finish') and source.get('compact') != 'yes' else None))
        except ValidationError as error:
            # Render current server state without applying stale form values.
            messages.error(request, ' '.join(error.messages))
            return redirect(link('practice_hub:start', group=group.pk, athlete=selected_id))
    rows = athlete_rows(gym_id, roster, today, event, group, session) if group else []
    now = timezone.now()
    timers = {timer.athlete_id: timer for timer in session.athlete_timers.all()} if session else {}
    for row in rows:
        timer = timers.get(row['athlete'].pk)
        default_event, default_minutes = child_timer_defaults(row['plan'])
        minutes = timer.minutes if timer else default_minutes
        row['timer'] = {**clock_values(timer.deadline if timer else None,
            timer.remaining_seconds if timer else minutes * 60, now),
            'version': timer.version if timer else 0, 'minutes': minutes,
            'event': timer.event if timer else default_event}
    selected_row = next((r for r in rows if r['athlete'].pk == selected_id), None)
    if selected_row:
        selected_id = selected_row['athlete'].pk
    choices = [{'code': code, 'label': label, 'url': link('practice_hub:start',
        group=group.pk if group else None, athlete=selected_id, event=code)} for code, label in EVENTS]
    next_event = EVENTS[(list(dict(EVENTS)).index(event) + 1) % len(EVENTS)][0]
    timer_until = group_deadline(session) if session and session.rotation_paused_seconds is None and not session.finished_at else None
    group_clock = clock_values(timer_until,
        session.rotation_paused_seconds if session and session.rotation_paused_seconds is not None else 900, now)
    return render(request, 'practice_hub/start.html', {
        'groups': groups, 'group': group, 'rows': rows, 'selected_row': selected_row,
        'selected_id': selected_id, 'session': session, 'today': today, 'event': event,
        'event_label': dict(EVENTS)[event], 'event_choices': choices, 'next_event': next_event,
        'timer_until': timer_until, 'group_clock': group_clock, 'attendance_choices': AttendanceRecord.STATUS_CHOICES,
        'tools_open': request.GET.get('tools') == '1',
        'present_count': sum(bool(r['attendance'] and r['attendance'].status in ('present', 'late')) for r in rows),
        'unrecorded_count': sum(r['attendance'] is None for r in rows),
        'pending_count': sum(r['pending'] for r in rows),
        'refresh_url': link('practice_hub:start', group=group.pk if group else None,
            athlete=selected_id, event=event),
    })
