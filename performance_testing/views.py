from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    TestingExerciseForm,
    TestingSessionForm,
)
from .models import (
    AthleteTestingResult,
    TestingExercise,
    TestingExerciseResult,
    TestingSession,
)
from .services import update_session_rankings
from django.urls import reverse


def coach_testing_required(user):
    return user.role in ['coach', 'head_coach']


def get_authorized_session(user, session_id):
    session = get_object_or_404(
        TestingSession.objects.prefetch_related(
            'exercises',
            'athletes'
        ),
        id=session_id
    )

    if user.role == 'head_coach':
        return session

    if session.created_by == user:
        return session

    return None


def parse_score(value):
    if value in [None, '']:
        return Decimal('0.00')

    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00')


def build_testing_grid(session):
    exercises = list(
        session.exercises.all().order_by(
            'display_order',
            'name'
        )
    )

    athlete_results = list(
        AthleteTestingResult.objects.filter(
            session=session
        ).select_related(
            'athlete',
            'entered_by',
            'verified_by'
        ).prefetch_related(
            'exercise_results__exercise'
        ).order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username'
        )
    )

    grid_rows = []

    for athlete_result in athlete_results:
        existing_results = {
            exercise_result.exercise_id: exercise_result
            for exercise_result
            in athlete_result.exercise_results.all()
        }

        cells = []

        for exercise in exercises:
            exercise_result = existing_results.get(exercise.id)

            if exercise_result is None:
                exercise_result = TestingExerciseResult.objects.create(
                    athlete_result=athlete_result,
                    exercise=exercise
                )

            cells.append({
                'exercise': exercise,
                'result': exercise_result,
            })

        grid_rows.append({
            'athlete_result': athlete_result,
            'cells': cells,
            'previous_score': athlete_result.previous_score,
            'score_change': athlete_result.score_change,
        })

    return exercises, grid_rows


@login_required
def testing_session_list(request):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.user.role == 'head_coach':
        sessions = TestingSession.objects.all()
    else:
        sessions = TestingSession.objects.filter(
            created_by=request.user
        )

    sessions = sessions.prefetch_related(
        'exercises',
        'athletes'
    ).order_by(
        '-testing_date',
        '-created_at'
    )

    session_data = []

    for session in sessions:
        result_count = AthleteTestingResult.objects.filter(
            session=session
        ).count()

        verified_count = AthleteTestingResult.objects.filter(
            session=session,
            status='verified'
        ).count()

        session_data.append({
            'session': session,
            'athlete_count': session.athletes.count(),
            'exercise_count': session.exercises.count(),
            'result_count': result_count,
            'verified_count': verified_count,
        })

    return render(
        request,
        'performance_testing/session_list.html',
        {
            'session_data': session_data,
        }
    )


@login_required
def create_testing_session(request):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method == 'POST':
        form = TestingSessionForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            form.save_m2m()

            for athlete in session.athletes.all():
                athlete_result, created = (
                    AthleteTestingResult.objects.get_or_create(
                        session=session,
                        athlete=athlete,
                        defaults={
                            'status': 'draft',
                            'entered_by': request.user,
                        }
                    )
                )

                for exercise in session.exercises.all():
                    TestingExerciseResult.objects.get_or_create(
                        athlete_result=athlete_result,
                        exercise=exercise
                    )

            messages.success(
                request,
                'Testing session created successfully.'
            )

            return redirect(
                'testing_session_detail',
                session_id=session.id
            )

    else:
        form = TestingSessionForm(user=request.user)

    return render(
        request,
        'performance_testing/create_session.html',
        {
            'form': form,
        }
    )


@login_required
@transaction.atomic
def testing_session_detail(request, session_id):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    session = get_authorized_session(
        request.user,
        session_id
    )

    if session is None:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    exercises, grid_rows = build_testing_grid(session)

    if request.method == 'POST':
        action = request.POST.get('action', 'save_draft')

        for row in grid_rows:
            athlete_result = row['athlete_result']

            for cell in row['cells']:
                exercise = cell['exercise']
                exercise_result = cell['result']

                raw_field = (
                    f'raw_{athlete_result.id}_{exercise.id}'
                )

                score_field = (
                    f'score_{athlete_result.id}_{exercise.id}'
                )

                not_completed_field = (
                    f'not_completed_'
                    f'{athlete_result.id}_{exercise.id}'
                )

                raw_result = request.POST.get(
                    raw_field,
                    ''
                ).strip()

                score_value = request.POST.get(
                    score_field,
                    ''
                ).strip()

                not_completed = (
                    request.POST.get(not_completed_field)
                    == 'on'
                )

                exercise_result.raw_result = raw_result
                exercise_result.not_completed = not_completed

                if not_completed:
                    exercise_result.score = Decimal('0.00')
                else:
                    exercise_result.score = parse_score(score_value)

                exercise_result.save()

            athlete_result.entered_by = request.user
            athlete_result.calculate_total_score()

            if action == 'verify':
                athlete_result.status = 'verified'
                athlete_result.verified_by = request.user
            else:
                athlete_result.status = 'draft'
                athlete_result.verified_by = None

            athlete_result.save(
                update_fields=[
                    'entered_by',
                    'status',
                    'verified_by',
                ]
            )

        update_session_rankings(session)

        if action == 'verify':
            messages.success(
                request,
                'Results verified and rankings calculated.'
            )
        else:
            messages.success(
                request,
                'Testing results saved as a draft.'
            )

        return redirect(
            'testing_session_detail',
            session_id=session.id
        )

    verified_count = AthleteTestingResult.objects.filter(
        session=session,
        status='verified'
    ).count()

    return render(
        request,
        'performance_testing/session_detail.html',
        {
            'session': session,
            'exercises': exercises,
            'grid_rows': grid_rows,
            'verified_count': verified_count,
        }
    )

@login_required
def testing_exercise_list(request):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    exercises = TestingExercise.objects.select_related(
        'created_by'
    ).order_by(
        'display_order',
        'name'
    )

    return render(
        request,
        'performance_testing/exercise_list.html',
        {
            'exercises': exercises,
        }
    )


@login_required
def create_testing_exercise(request):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method == 'POST':
        form = TestingExerciseForm(request.POST)

        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.created_by = request.user
            exercise.save()

            messages.success(
                request,
                f'{exercise.name} was added to the Exercise Library.'
            )

            next_url = request.POST.get('next')

            if next_url == 'create_session':
                return redirect('create_testing_session')

            return redirect('testing_exercise_list')

    else:
        form = TestingExerciseForm(initial={
            'active': True,
            'higher_is_better': True,
        })

    return render(
        request,
        'performance_testing/exercise_form.html',
        {
            'form': form,
            'page_title': 'Create Testing Exercise',
            'button_text': 'Create Exercise',
            'exercise': None,
        }
    )


@login_required
def edit_testing_exercise(request, exercise_id):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    exercise = get_object_or_404(
        TestingExercise,
        id=exercise_id
    )

    if (
        request.user.role != 'head_coach'
        and exercise.created_by != request.user
    ):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method == 'POST':
        form = TestingExerciseForm(
            request.POST,
            instance=exercise
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f'{exercise.name} was updated.'
            )

            return redirect('testing_exercise_list')

    else:
        form = TestingExerciseForm(instance=exercise)

    return render(
        request,
        'performance_testing/exercise_form.html',
        {
            'form': form,
            'page_title': 'Edit Testing Exercise',
            'button_text': 'Save Changes',
            'exercise': exercise,
        }
    )


@login_required
def toggle_testing_exercise(request, exercise_id):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    exercise = get_object_or_404(
        TestingExercise,
        id=exercise_id
    )

    if (
        request.user.role != 'head_coach'
        and exercise.created_by != request.user
    ):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method == 'POST':
        exercise.active = not exercise.active
        exercise.save(update_fields=['active'])

        status = 'activated' if exercise.active else 'deactivated'

        messages.success(
            request,
            f'{exercise.name} was {status}.'
        )

    return redirect('testing_exercise_list')

@login_required
def athlete_testing_history(request):
    if request.user.role != 'athlete':
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete_results = list(
        AthleteTestingResult.objects.filter(
            athlete=request.user,
            status='verified',
            session__published_to_athletes=True
        ).select_related(
            'session',
            'verified_by'
        ).prefetch_related(
            'exercise_results__exercise'
        ).order_by(
            '-session__testing_date',
            '-session__created_at'
        )
    )

    history_rows = []

    for result in athlete_results:
        previous_result = result.get_previous_result()
        score_change = None

        if previous_result:
            score_change = (
                result.total_score
                - previous_result.total_score
            )

        history_rows.append({
            'result': result,
            'previous_score': (
                previous_result.total_score
                if previous_result
                else None
            ),
            'score_change': score_change,
        })

    chart_results = list(reversed(athlete_results))

    chart_labels = [
        result.session.testing_date.strftime('%b %d')
        for result in chart_results
    ]

    chart_scores = [
        float(result.total_score)
        for result in chart_results
    ]

    latest_result = (
        athlete_results[0]
        if athlete_results
        else None
    )

    personal_best = None

    if athlete_results:
        personal_best = max(
            athlete_results,
            key=lambda result: result.total_score
        )

    return render(
        request,
        'performance_testing/athlete_history.html',
        {
            'history_rows': history_rows,
            'latest_result': latest_result,
            'personal_best': personal_best,
            'chart_labels': chart_labels,
            'chart_scores': chart_scores,
        }
    )


@login_required
def athlete_testing_result_detail(request, result_id):
    if request.user.role != 'athlete':
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete_result = get_object_or_404(
        AthleteTestingResult.objects.select_related(
            'session',
            'verified_by'
        ).prefetch_related(
            'exercise_results__exercise'
        ),
        id=result_id,
        athlete=request.user,
        status='verified',
        session__published_to_athletes=True
    )

    exercise_results = athlete_result.exercise_results.select_related(
        'exercise'
    ).order_by(
        'exercise__display_order',
        'exercise__name'
    )

    previous_result = athlete_result.get_previous_result()

    previous_score = None
    score_change = None

    if previous_result:
        previous_score = previous_result.total_score
        score_change = (
            athlete_result.total_score
            - previous_result.total_score
        )

    return render(
        request,
        'performance_testing/athlete_result_detail.html',
        {
            'athlete_result': athlete_result,
            'exercise_results': exercise_results,
            'previous_score': previous_score,
            'score_change': score_change,
        }
    )



@login_required
@transaction.atomic
def publish_testing_session(request, session_id):
    if not coach_testing_required(request.user):
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    session = get_authorized_session(
        request.user,
        session_id
    )

    if session is None:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method != 'POST':
        return redirect(
            'testing_session_detail',
            session_id=session.id
        )

    total_results = AthleteTestingResult.objects.filter(
        session=session
    ).count()

    verified_results = AthleteTestingResult.objects.filter(
        session=session,
        status='verified'
    ).count()

    if total_results == 0:
        messages.error(
            request,
            'This testing session does not have any athlete results.'
        )

        return redirect(
            'testing_session_detail',
            session_id=session.id
        )

    if verified_results != total_results:
        messages.error(
            request,
            (
                'All athlete results must be verified before '
                'the session can be published.'
            )
        )

        return redirect(
            'testing_session_detail',
            session_id=session.id
        )

    publish_target = request.POST.get('publish_target')

    if publish_target == 'athletes':
        session.published_to_athletes = True
        session.save(update_fields=['published_to_athletes'])

        messages.success(
            request,
            'Testing results were published to athletes.'
        )

    elif publish_target == 'parents':
        session.published_to_parents = True
        session.save(update_fields=['published_to_parents'])

        messages.success(
            request,
            'Testing results were published to parents.'
        )

    elif publish_target == 'both':
        session.published_to_athletes = True
        session.published_to_parents = True

        session.save(update_fields=[
            'published_to_athletes',
            'published_to_parents',
        ])

        messages.success(
            request,
            'Testing results were published to athletes and parents.'
        )

    elif publish_target == 'unpublish_athletes':
        session.published_to_athletes = False
        session.save(update_fields=['published_to_athletes'])

        messages.success(
            request,
            'Testing results were hidden from athletes.'
        )

    elif publish_target == 'unpublish_parents':
        session.published_to_parents = False
        session.save(update_fields=['published_to_parents'])

        messages.success(
            request,
            'Testing results were hidden from parents.'
        )

    else:
        messages.error(
            request,
            'A valid publishing option was not selected.'
        )

    return redirect(
        'testing_session_detail',
        session_id=session.id
    )
