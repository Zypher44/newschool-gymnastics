from datetime import (
    datetime,
    timedelta,
)
import json

from parents_portal.access import get_approved_parent_links, get_parent_gym_ids
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from gyms.tenant import single_active_gym_id
from gyms.models import TrainingGroupAthlete

from .models import (
    DailyRoutineAttempt,
    DailyRoutineSession,
)


User = get_user_model()


EVENTS = [
    {
        'code': 'vault',
        'name': 'Vault',
        'icon': '🏃',
    },
    {
        'code': 'bars',
        'name': 'Bars',
        'icon': '🤸',
    },
    {
        'code': 'beam',
        'name': 'Beam',
        'icon': '⚖️',
    },
    {
        'code': 'floor',
        'name': 'Floor',
        'icon': '🎵',
    },
]


def coach_allowed(
    user,
):
    return (
        user.is_authenticated
        and
        user.role in [
            'coach',
            'head_coach',
        ]
        and single_active_gym_id(user, ['coach', 'head_coach']) is not None
    )


def build_stats(
    attempts,
):
    attempts = list(
        attempts
    )

    attempt_count = len(
        attempts
    )

    wow_count = sum(
        1
        for attempt in attempts
        if (
            attempt.result
            ==
            DailyRoutineAttempt.RESULT_WOW
        )
    )

    hit_count = sum(
        1
        for attempt in attempts
        if (
            attempt.result
            ==
            DailyRoutineAttempt.RESULT_HIT
        )
    )

    missed_count = sum(
        1
        for attempt in attempts
        if (
            attempt.result
            ==
            DailyRoutineAttempt.RESULT_MISSED
        )
    )


    if attempt_count:

        success_count = (
            wow_count
            + hit_count
        )

        hit_rate = round(
            (success_count / attempt_count) * 100
        )

    else:
        success_count = 0
        hit_rate = 0

    return {
        'attempts': attempt_count,
        'wows': wow_count,
        'hits': hit_count,
        'missed': missed_count,
        'success_count': success_count,
        'hit_rate': hit_rate,
    }


@login_required
def daily_routine_tracker(
    request,
):
    if not coach_allowed(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can access '
                'the Daily Routine Tracker.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    date_string = (
        request.GET.get(
            'date'
        )
    )


    if date_string:

        try:

            practice_date = (
                datetime.strptime(
                    date_string,
                    '%Y-%m-%d',
                )
                .date()
            )

        except ValueError:

            practice_date = (
                timezone.localdate()
            )

    else:

        practice_date = (
            timezone.localdate()
        )


    session, created = (
        DailyRoutineSession.objects
        .get_or_create(
            gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']),
            practice_date=(
                practice_date
            ),

            defaults={
                'created_by': (
                    request.user
                ),
            },
        )
    )


    athletes = (
        User.objects
        .filter(
            role='athlete',
            is_active=True,
            gym_memberships__gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']),
            gym_memberships__role='athlete', gym_memberships__is_active=True,
        )
        .order_by(
            'first_name',
            'last_name',
            'username',
        )
    )


    attempts = list(
        DailyRoutineAttempt.objects
        .filter(
            session=session,
        )
        .select_related(
            'athlete',
            'recorded_by',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
            'event',
            'attempt_number',
        )
    )


    athlete_rows = []


    for athlete in athletes:

        event_rows = []


        for event in EVENTS:

            event_attempts = [
                attempt
                for attempt in attempts
                if (
                    attempt.athlete_id
                    ==
                    athlete.id
                    and
                    attempt.event
                    ==
                    event['code']
                )
            ]

            regular_attempts = [a for a in event_attempts if not a.is_pressure]
            pressure_attempts = [a for a in event_attempts if a.is_pressure]


            event_rows.append({
                'event': event,

                'attempt_list': (
                    event_attempts
                ),

                'regular_attempts': regular_attempts,
                'pressure_attempts': pressure_attempts,
                'tracks': [
                    {
                        'label': 'Routine',
                        'is_pressure': False,
                        'attempts': regular_attempts,
                    },
                    {
                        'label': 'Pressure set',
                        'is_pressure': True,
                        'attempts': pressure_attempts,
                    },
                ],

                'stats': build_stats(event_attempts),
                'routine_stats': build_stats(regular_attempts),
                'pressure_stats': build_stats(pressure_attempts),
            })


        athlete_attempts = [
            attempt
            for attempt in attempts
            if (
                attempt.athlete_id
                ==
                athlete.id
            )
        ]


        athlete_rows.append({
            'athlete': athlete,

            'events': (
                event_rows
            ),

            'overall': (
                build_stats(
                    athlete_attempts
                )
            ),
        })


    overall_stats = (
        build_stats(
            attempts
        )
    )


    context = {
        'session': session,

        'practice_date': (
            practice_date
        ),

        'athlete_rows': (
            athlete_rows
        ),

        'overall_stats': (
            overall_stats
        ),

        'events': EVENTS,
    }


    # Routine template diagnostic
    from django.template.loader import get_template
    print('ACTIVE ROUTINE TEMPLATE:', get_template('routine_tracker/daily_routine_tracker.html').origin.name, flush=True)

    return render(
        request,
        (
            'routine_tracker/'
            'daily_routine_tracker.html'
        ),
        context,
    )


@login_required
@require_POST
def add_routine_attempt(
    request,
):
    if not coach_allowed(
        request.user
    ):

        return redirect(
            'role_redirect'
        )


    session = get_object_or_404(
        DailyRoutineSession.objects.filter(gym_id=single_active_gym_id(request.user, ['coach', 'head_coach'])),
        id=(
            request.POST.get(
                'session_id'
            )
        ),
    )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
            gym_memberships__gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']),
            gym_memberships__role='athlete', gym_memberships__is_active=True,
        ),
        id=(
            request.POST.get(
                'athlete_id'
            )
        ),
    )


    event = (
        request.POST.get(
            'event',
            ''
        )
        .strip()
    )


    result = (
        request.POST.get(
            'result',
            ''
        )
        .strip()
    )

    is_pressure = request.POST.get('is_pressure') == 'true'


    valid_events = {
        choice[0]
        for choice
        in (
            DailyRoutineAttempt
            .EVENT_CHOICES
        )
    }


    valid_results = {
        choice[0]
        for choice
        in (
            DailyRoutineAttempt
            .RESULT_CHOICES
        )
    }


    if (
        event not in valid_events
        or
        result not in valid_results
    ):

        messages.error(
            request,
            'Invalid routine attempt.',
        )

        url = reverse(
            (
                'routine_tracker:'
                'daily_routine_tracker'
            )
        )

        return redirect(
            (
                f'{url}'
                f'?date={session.practice_date}'
            )
        )


    max_attempt = (
        DailyRoutineAttempt.objects
        .filter(
            session=session,
            athlete=athlete,
            event=event,
            is_pressure=is_pressure,
        )
        .aggregate(
            max_attempt=Max(
                'attempt_number'
            )
        )
        .get(
            'max_attempt'
        )
        or 0
    )


    DailyRoutineAttempt.objects.create(
        session=session,

        athlete=athlete,

        event=event,

        attempt_number=(
            max_attempt + 1
        ),

        result=result,

        is_pressure=is_pressure,

        recorded_by=(
            request.user
        ),
    )


    url = reverse(
        (
            'routine_tracker:'
            'daily_routine_tracker'
        )
    )


    return redirect(
        (
            f'{url}'
            f'?date={session.practice_date}'
        )
    )


@login_required
@require_POST
def save_routine_practice(request):
    """Save a coach's staged tracker changes in one request."""
    if not coach_allowed(request.user):
        return JsonResponse({'ok': False, 'error': 'Coach access required.'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        session_id = payload.get('session_id')
        operations = payload.get('operations', [])
        if not isinstance(operations, list) or len(operations) > 1000:
            raise ValueError
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid save data.'}, status=400)

    gym_id = single_active_gym_id(request.user, ['coach', 'head_coach'])
    session = get_object_or_404(DailyRoutineSession.objects.filter(gym_id=gym_id), pk=session_id)
    athletes = User.objects.filter(
        role='athlete', is_active=True,
        gym_memberships__gym_id=gym_id,
        gym_memberships__role='athlete', gym_memberships__is_active=True,
    ).distinct()
    valid_events = {choice[0] for choice in DailyRoutineAttempt.EVENT_CHOICES}
    valid_results = {choice[0] for choice in DailyRoutineAttempt.RESULT_CHOICES}

    # Validate the complete request before writing any part of it.
    for operation in operations:
        if not isinstance(operation, dict):
            return JsonResponse({'ok': False, 'error': 'Invalid change in save data.'}, status=400)
        if 'delete_id' in operation:
            if not str(operation['delete_id']).isdigit():
                return JsonResponse({'ok': False, 'error': 'Invalid removal request.'}, status=400)
            if not DailyRoutineAttempt.objects.filter(
                pk=operation['delete_id'], session=session
            ).exists():
                return JsonResponse({'ok': False, 'error': 'An attempt could not be found.'}, status=400)
            continue
        if (
            str(operation.get('athlete_id', '')).isdigit() is False
            or not athletes.filter(pk=operation.get('athlete_id')).exists()
            or operation.get('event') not in valid_events
            or operation.get('result') not in valid_results
            or not isinstance(operation.get('is_pressure', False), bool)
        ):
            return JsonResponse({'ok': False, 'error': 'One or more changes are invalid.'}, status=400)

    with transaction.atomic():
        session = DailyRoutineSession.objects.select_for_update().get(pk=session.pk)
        deleted = [op['delete_id'] for op in operations if 'delete_id' in op]
        if deleted:
            DailyRoutineAttempt.objects.filter(pk__in=deleted, session=session).delete()

        next_numbers = {}
        saved = 0
        for operation in operations:
            if 'delete_id' in operation:
                continue
            athlete_id = int(operation['athlete_id'])
            event = operation['event']
            is_pressure = operation.get('is_pressure', False)
            key = (athlete_id, event, is_pressure)
            if key not in next_numbers:
                next_numbers[key] = (
                    DailyRoutineAttempt.objects.filter(
                        session=session, athlete_id=athlete_id, event=event,
                        is_pressure=is_pressure,
                    ).aggregate(max_number=Max('attempt_number'))['max_number'] or 0
                )
            next_numbers[key] += 1
            DailyRoutineAttempt.objects.create(
                session=session,
                athlete_id=athlete_id,
                event=event,
                is_pressure=is_pressure,
                attempt_number=next_numbers[key],
                result=operation['result'],
                recorded_by=request.user,
            )
            saved += 1

    return JsonResponse({'ok': True, 'saved': saved, 'deleted': len(deleted)})


@login_required
@require_POST
def delete_routine_attempt(
    request,
    attempt_id,
):
    if not coach_allowed(
        request.user
    ):

        return redirect(
            'role_redirect'
        )


    attempt = get_object_or_404(
        DailyRoutineAttempt.objects
        .filter(session__gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']))
        .select_related(
            'session',
        ),
        id=attempt_id,
    )


    practice_date = (
        attempt.session.practice_date
    )


    attempt.delete()


    url = reverse(
        (
            'routine_tracker:'
            'daily_routine_tracker'
        )
    )


    return redirect(
        (
            f'{url}'
            f'?date={practice_date}'
        )
    )


def build_group_quick_comparison(user, athlete, attempts, gym_id):
    """Compare a gymnast's 7-day counts with active peers in coach-assigned groups."""
    group_ids = list(TrainingGroupAthlete.objects.filter(
        athlete=athlete,
        is_active=True,
        group__gym_id=gym_id,
        group__is_active=True,
        group__coach_assignments__coach=user,
    ).values_list('group_id', flat=True).distinct())
    if not group_ids:
        return []

    peer_ids = set(TrainingGroupAthlete.objects.filter(
        group_id__in=group_ids,
        group__gym_id=gym_id,
        is_active=True,
        group__is_active=True,
        athlete__is_active=True,
        athlete__gym_memberships__gym_id=gym_id,
        athlete__gym_memberships__role='athlete',
        athlete__gym_memberships__is_active=True,
    ).values_list('athlete_id', flat=True))
    if athlete.pk not in peer_ids:
        peer_ids.add(athlete.pk)

    results = (
        DailyRoutineAttempt.RESULT_WOW,
        DailyRoutineAttempt.RESULT_HIT,
        DailyRoutineAttempt.RESULT_MISSED,
    )
    peer_attempts = [attempt for attempt in attempts if attempt.athlete_id in peer_ids]
    comparison = []
    for event in EVENTS:
        for is_pressure, context_label in ((False, 'Routine'), (True, 'Pressure set')):
            counts_by_athlete = {peer_id: {result: 0 for result in results} for peer_id in peer_ids}
            for attempt in peer_attempts:
                if attempt.event == event['code'] and attempt.is_pressure == is_pressure:
                    counts_by_athlete[attempt.athlete_id][attempt.result] += 1
            active_peers = [counts for counts in counts_by_athlete.values() if sum(counts.values())]
            child_counts = counts_by_athlete.get(athlete.pk, {result: 0 for result in results})
            if not active_peers:
                continue
            comparison.append({
                'event': event['name'],
                'context': context_label,
                'athlete_counts': child_counts,
                'group_average': {
                    result: round(sum(counts[result] for counts in active_peers) / len(active_peers), 1)
                    for result in results
                },
                'group_athletes': len(active_peers),
            })
    return comparison


@login_required
def routine_consistency_summary(
    request,
):
    if not coach_allowed(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can access '
                'routine consistency reports.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    end_date = timezone.localdate()

    start_date = (
            end_date
            -
            timedelta(
                days=6
            )
    )


    athletes = (
        User.objects
        .filter(
            role='athlete',
            is_active=True,
            gym_memberships__gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']),
            gym_memberships__role='athlete', gym_memberships__is_active=True,
        )
        .order_by(
            'first_name',
            'last_name',
            'username',
        )
    )


    attempts = list(
        DailyRoutineAttempt.objects
        .filter(
            session__gym_id=single_active_gym_id(request.user, ['coach', 'head_coach']),
            session__practice_date__range=[
                start_date,
                end_date,
            ],
        )
        .select_related(
            'athlete',
            'session',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'session__practice_date',
            'event',
            'attempt_number',
        )
    )


    gym_id = single_active_gym_id(request.user, ['coach', 'head_coach'])
    athlete_rows = []


    for athlete in athletes:

        athlete_attempts = [
            attempt
            for attempt in attempts
            if (
                attempt.athlete_id
                ==
                athlete.id
            )
        ]


        event_rows = []


        for event in EVENTS:

            event_attempts = [
                attempt
                for attempt
                in athlete_attempts
                if (
                    attempt.event
                    ==
                    event['code']
                )
            ]


            routine_attempts = [a for a in event_attempts if not a.is_pressure]
            pressure_attempts = [a for a in event_attempts if a.is_pressure]
            event_rows.append({
                'event': event,
                'stats': build_stats(event_attempts),
                'routine_stats': build_stats(routine_attempts),
                'pressure_stats': build_stats(pressure_attempts),
            })


        athlete_rows.append({
            'athlete': athlete,

            'events': (
                event_rows
            ),

            'overall': (
                build_stats(
                    athlete_attempts
                )
            ),
            'group_comparison': build_group_quick_comparison(
                request.user, athlete, attempts, gym_id
            ),
        })


    overall_stats = (
        build_stats(
            attempts
        )
    )


    context = {
        'start_date': start_date,

        'end_date': end_date,

        'athlete_rows': (
            athlete_rows
        ),

        'overall_stats': (
            overall_stats
        ),
    }


    return render(
        request,
        (
            'routine_tracker/'
            'routine_consistency_summary.html'
        ),
        context,
    )

# ============================================================
# ATHLETE ROUTINE CONSISTENCY HELPER
# ============================================================


def build_athlete_consistency(
    athlete,
    days=7,
    gym_ids=None,
):
    end_date = (
        timezone.localdate()
    )

    start_date = (
        end_date
        -
        timedelta(
            days=days - 1
        )
    )


    attempts_query = DailyRoutineAttempt.objects.filter(
            athlete=athlete,
            session__practice_date__range=[
                start_date,
                end_date,
            ],
        )
    if gym_ids is not None:
        attempts_query = attempts_query.filter(session__gym_id__in=gym_ids)
    attempts = list(
        attempts_query
        .select_related(
            'session',
            'recorded_by',
        )
        .order_by(
            'session__practice_date',
            'event',
            'attempt_number',
        )
    )


    event_rows = []


    for event in EVENTS:

        event_attempts = [
            attempt
            for attempt in attempts
            if (
                attempt.event
                ==
                event['code']
            )
        ]


        routine_attempts = [a for a in event_attempts if not a.is_pressure]
        pressure_attempts = [a for a in event_attempts if a.is_pressure]
        event_rows.append({
            'event': event,
            'stats': build_stats(event_attempts),
            'routine_stats': build_stats(routine_attempts),
            'pressure_stats': build_stats(pressure_attempts),
        })


    return {
        'start_date': start_date,
        'end_date': end_date,
        'event_rows': event_rows,
        'overall': (
            build_stats(
                attempts
            )
        ),
    }


# ============================================================
# ATHLETE — MY ROUTINE CONSISTENCY
# ============================================================


@login_required
def athlete_routine_consistency(
    request,
):
    if request.user.role != 'athlete':

        messages.error(
            request,
            (
                'This page is available '
                'to athletes only.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    summary = (
        build_athlete_consistency(
            request.user
        )
    )


    context = {
        'athlete': request.user,

        'viewer_type': 'athlete',

        'start_date': (
            summary[
                'start_date'
            ]
        ),

        'end_date': (
            summary[
                'end_date'
            ]
        ),

        'event_rows': (
            summary[
                'event_rows'
            ]
        ),

        'overall_stats': (
            summary[
                'overall'
            ]
        ),
    }


    return render(
        request,
        (
            'routine_tracker/'
            'athlete_routine_consistency.html'
        ),
        context,
    )


# ============================================================
# PARENT — ROUTINE CONSISTENCY HOME
# ============================================================


@login_required
def parent_routine_consistency_home(
    request,
):
    if request.user.role != 'parent':

        messages.error(
            request,
            (
                'This page is available '
                'to parents only.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    links = (
        get_approved_parent_links(request.user)
        .select_related(
            'athlete',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )


    from parents_portal.selection import selected_child
    child = selected_child(request)
    first_link = links.filter(athlete=child).first() if child else None

    if not first_link:

        messages.info(
            request,
            (
                'No athletes are currently '
                'linked to your account.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    return redirect(
        'routine_tracker:parent_routine_consistency',
        athlete_id=(
            first_link.athlete_id
        ),
    )


# ============================================================
# PARENT — CHILD ROUTINE CONSISTENCY
# ============================================================


@login_required
def parent_routine_consistency(
    request,
    athlete_id,
):
    if request.user.role != 'parent':

        messages.error(
            request,
            (
                'This page is available '
                'to parents only.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    links = (
        get_approved_parent_links(request.user)
        .select_related(
            'athlete',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )


    athlete_link = get_object_or_404(
        links,
        athlete_id=athlete_id,
    )


    athlete = (
        athlete_link.athlete
    )


    summary = (
        build_athlete_consistency(
            athlete,
            gym_ids=get_parent_gym_ids(request.user),
        )
    )


    linked_athletes = [
        link.athlete
        for link
        in links
    ]


    context = {
        'athlete': athlete,

        'viewer_type': 'parent',

        'linked_athletes': (
            linked_athletes
        ),

        'start_date': (
            summary[
                'start_date'
            ]
        ),

        'end_date': (
            summary[
                'end_date'
            ]
        ),

        'event_rows': (
            summary[
                'event_rows'
            ]
        ),

        'overall_stats': (
            summary[
                'overall'
            ]
        ),
    }


    return render(
        request,
        (
            'routine_tracker/'
            'athlete_routine_consistency.html'
        ),
        context,
    )
