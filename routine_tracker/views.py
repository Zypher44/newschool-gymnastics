from datetime import (
    datetime,
    timedelta,
)

from parents_portal.models import (
    ParentAthleteLink,
)
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

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
            (
                success_count
                /
                attempt_count
            )
            * 100
        )

        quality = round(
            (
                (
                    wow_count
                    +
                    (
                        hit_count
                        * 0.5
                    )
                )
                /
                attempt_count
            )
            * 100
        )

    else:

        success_count = 0
        hit_rate = 0
        quality = 0


    return {
        'attempts': attempt_count,
        'wows': wow_count,
        'hits': hit_count,
        'missed': missed_count,
        'success_count': success_count,
        'hit_rate': hit_rate,
        'quality': quality,
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


            event_rows.append({
                'event': event,

                'attempt_list': (
                    event_attempts
                ),

                'stats': (
                    build_stats(
                        event_attempts
                    )
                ),
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
        DailyRoutineSession,
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


            event_rows.append({
                'event': event,

                'stats': (
                    build_stats(
                        event_attempts
                    )
                ),
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


    attempts = list(
        DailyRoutineAttempt.objects
        .filter(
            athlete=athlete,
            session__practice_date__range=[
                start_date,
                end_date,
            ],
        )
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


        event_rows.append({
            'event': event,

            'stats': (
                build_stats(
                    event_attempts
                )
            ),
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
        ParentAthleteLink.objects
        .filter(
            parent=request.user,
            approved=True,
        )
        .select_related(
            'athlete',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )


    first_link = (
        links.first()
    )


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
        ParentAthleteLink.objects
        .filter(
            parent=request.user,
            approved=True,
        )
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
            athlete
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
