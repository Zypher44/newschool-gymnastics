from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from performance_testing.models import TestingSession
import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import (
    CreatePracticeFromTemplateForm,
    PracticeAthleteAssignmentForm,
    PracticePlanForm,
    PracticeRotationForm,
    PracticeStationForm,
    SavePracticeTemplateForm,
    TrainingGroupForm,
)
from .models import (
    PracticeAthleteAssignment,
    PracticePlan,
    PracticeRotation,
    PracticeStation,
    PracticeTemplate,
    PracticeTemplateRotation,
    PracticeTemplateStation,
    TrainingGroup,
)

COACH_ROLES = [
    'coach',
    'head_coach',
]


def user_is_coach(user):
    return (
            user.is_authenticated
            and user.role in COACH_ROLES
    )


def coach_access_denied(request):
    messages.error(
        request,
        'Only coaches and head coaches can access the Practice Planner.',
    )

    return redirect(
        'role_redirect',
    )


def get_accessible_groups(user):
    """
    Head coaches can access every active training group.

    Regular coaches can only access groups where they are
    listed as a coach.
    """

    groups = TrainingGroup.objects.all()

    if user.role == 'head_coach':
        return groups

    return groups.filter(
        coaches=user,
    ).distinct()


def get_accessible_practices(user):
    """
    Return practices that the current coach is allowed to manage.
    """

    practices = PracticePlan.objects.select_related(
        'training_group',
        'lead_coach',
        'created_by',
    ).prefetch_related(
        'assistant_coaches',
        'rotations',
    )

    if user.role == 'head_coach':
        return practices

    return practices.filter(
        Q(training_group__coaches=user)
        | Q(lead_coach=user)
        | Q(assistant_coaches=user)
        | Q(created_by=user)
    ).distinct()


def get_accessible_testing_sessions(user):
    """
    Return testing sessions the current coach may use.
    """

    sessions = TestingSession.objects.select_related(
        'training_group',
        'practice_plan',
        'created_by',
    ).prefetch_related(
        'exercises',
        'athletes',
    )

    if user.role == 'head_coach':
        return sessions

    return sessions.filter(
        Q(created_by=user)
        | Q(training_group__coaches=user)
        | Q(practice_plan__lead_coach=user)
        | Q(practice_plan__assistant_coaches=user)
    ).distinct()


@login_required
def practice_dashboard(request):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    today = timezone.localdate()

    practices = get_accessible_practices(
        request.user
    )

    upcoming_practices = (
        practices.filter(
            practice_date__gte=today,
        )
        .exclude(
            status=PracticePlan.STATUS_CANCELLED,
        )
        .order_by(
            'practice_date',
            'start_time',
        )[:10]
    )

    draft_practices = (
        practices.filter(
            status=PracticePlan.STATUS_DRAFT,
        )
        .order_by(
            '-updated_at',
        )[:10]
    )

    in_progress_practices = (
        practices.filter(
            status=PracticePlan.STATUS_IN_PROGRESS,
        )
        .order_by(
            'practice_date',
            'start_time',
        )[:10]
    )

    completed_practices = (
        practices.filter(
            status=PracticePlan.STATUS_COMPLETED,
        )
        .order_by(
            '-practice_date',
            '-start_time',
        )[:10]
    )

    groups = get_accessible_groups(
        request.user
    ).filter(
        is_active=True,
    )

    context = {
        'today': today,
        'upcoming_practices': upcoming_practices,
        'draft_practices': draft_practices,
        'in_progress_practices': in_progress_practices,
        'completed_practices': completed_practices,
        'groups': groups,
        'upcoming_count': practices.filter(
            practice_date__gte=today,
        ).exclude(
            status=PracticePlan.STATUS_CANCELLED,
        ).count(),
        'draft_count': practices.filter(
            status=PracticePlan.STATUS_DRAFT,
        ).count(),
        'completed_count': practices.filter(
            status=PracticePlan.STATUS_COMPLETED,
        ).count(),
        'group_count': groups.count(),
    }

    return render(
        request,
        'practice_planner/dashboard.html',
        context,
    )


@login_required
def training_group_list(request):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    groups = (
        get_accessible_groups(request.user)
        .prefetch_related(
            'coaches',
            'athletes',
        )
        .order_by(
            'name',
        )
    )

    context = {
        'groups': groups,
    }

    return render(
        request,
        'practice_planner/training_group_list.html',
        context,
    )
@login_required
def practice_template_list(request):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    search_query = request.GET.get(
        'search',
        '',
    ).strip()

    category_filter = request.GET.get(
        'category',
        '',
    ).strip()

    ownership_filter = request.GET.get(
        'ownership',
        'all',
    ).strip()

    templates = (
        PracticeTemplate.objects
        .select_related(
            'created_by',
            'source_practice',
        )
        .prefetch_related(
            'rotations__stations',
        )
        .filter(
            is_active=True,
        )
    )

    if request.user.role == 'head_coach':
        templates = templates.filter(
            Q(created_by=request.user)
            | Q(is_shared=True)
        )
    else:
        templates = templates.filter(
            Q(created_by=request.user)
            | Q(is_shared=True)
        )

    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(level__icontains=search_query)
            | Q(season_phase__icontains=search_query)
            | Q(primary_focus__icontains=search_query)
        )

    if category_filter:
        templates = templates.filter(
            category=category_filter,
        )

    if ownership_filter == 'mine':
        templates = templates.filter(
            created_by=request.user,
        )

    elif ownership_filter == 'shared':
        templates = templates.filter(
            is_shared=True,
        ).exclude(
            created_by=request.user,
        )

    templates = templates.order_by(
        '-updated_at',
        'name',
    )

    context = {
        'templates': templates,
        'search_query': search_query,
        'category_filter': category_filter,
        'ownership_filter': ownership_filter,
        'category_choices': (
            PracticeTemplate.CATEGORY_CHOICES
        ),
    }

    return render(
        request,
        'practice_planner/template_list.html',
        context,
    )


@login_required
def practice_template_detail(
    request,
    template_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_template = get_object_or_404(
        PracticeTemplate.objects
        .select_related(
            'created_by',
            'source_practice',
        )
        .prefetch_related(
            'rotations__stations',
        )
        .filter(
            Q(created_by=request.user)
            | Q(is_shared=True)
        ),
        id=template_id,
        is_active=True,
    )

    rotations = (
        practice_template.rotations
        .prefetch_related(
            'stations',
        )
        .order_by(
            'order',
        )
    )

    total_station_count = sum(
        rotation.stations.count()
        for rotation in rotations
    )

    context = {
        'practice_template': practice_template,
        'rotations': rotations,
        'total_station_count': total_station_count,
    }

    return render(
        request,
        'practice_planner/template_detail.html',
        context,
    )

@login_required
def training_group_create(request):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    if request.method == 'POST':
        form = TrainingGroupForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            with transaction.atomic():
                training_group = form.save()

                if request.user.role == 'coach':
                    training_group.coaches.add(
                        request.user
                    )

            messages.success(
                request,
                (
                    f'Training group '
                    f'"{training_group.name}" was created.'
                ),
            )

            return redirect(
                'practice_planner:training_group_detail',
                group_id=training_group.id,
            )

    else:
        form = TrainingGroupForm(
            user=request.user,
        )

    context = {
        'form': form,
        'page_title': 'Create Training Group',
        'submit_label': 'Create Group',
    }

    return render(
        request,
        'practice_planner/training_group_form.html',
        context,
    )


@login_required
def training_group_detail(
        request,
        group_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    training_group = get_object_or_404(
        get_accessible_groups(
            request.user
        ).prefetch_related(
            'coaches',
            'athletes',
        ),
        id=group_id,
    )

    practices = (
        training_group.practice_plans
        .select_related(
            'lead_coach',
        )
        .prefetch_related(
            'rotations',
        )
        .order_by(
            '-practice_date',
            '-start_time',
        )
    )

    testing_sessions = (
        training_group.testing_sessions
        .prefetch_related(
            'exercises',
            'athletes',
        )
        .order_by(
            '-testing_date',
        )
    )

    context = {
        'training_group': training_group,
        'practices': practices,
        'testing_sessions': testing_sessions,
    }

    return render(
        request,
        'practice_planner/training_group_detail.html',
        context,
    )


@login_required
def training_group_update(
        request,
        group_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    training_group = get_object_or_404(
        get_accessible_groups(
            request.user
        ),
        id=group_id,
    )

    if request.method == 'POST':
        form = TrainingGroupForm(
            request.POST,
            instance=training_group,
            user=request.user,
        )

        if form.is_valid():
            training_group = form.save()

            if request.user.role == 'coach':
                training_group.coaches.add(
                    request.user
                )

            messages.success(
                request,
                (
                    f'Training group '
                    f'"{training_group.name}" was updated.'
                ),
            )

            return redirect(
                'practice_planner:training_group_detail',
                group_id=training_group.id,
            )

    else:
        form = TrainingGroupForm(
            instance=training_group,
            user=request.user,
        )

    context = {
        'form': form,
        'training_group': training_group,
        'page_title': 'Edit Training Group',
        'submit_label': 'Save Changes',
    }

    return render(
        request,
        'practice_planner/training_group_form.html',
        context,
    )


@login_required
def practice_create(request):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    initial_data = {}

    group_id = request.GET.get(
        'group'
    )

    if group_id:
        training_group = get_object_or_404(
            get_accessible_groups(
                request.user
            ),
            id=group_id,
        )

        initial_data['training_group'] = (
            training_group
        )

    if request.method == 'POST':
        form = PracticePlanForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            with transaction.atomic():
                practice_plan = form.save(
                    commit=False
                )

                practice_plan.created_by = (
                    request.user
                )

                practice_plan.save()

                form.save_m2m()

                create_default_athlete_assignments(
                    practice_plan
                )

            messages.success(
                request,
                (
                    f'Practice "{practice_plan.title}" '
                    f'was created.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticePlanForm(
            user=request.user,
            initial=initial_data,
        )

    context = {
        'form': form,
        'page_title': 'Create Practice',
        'submit_label': 'Create Practice',
    }

    return render(
        request,
        'practice_planner/practice_form.html',
        context,
    )


@login_required
def practice_detail(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    rotations = (
        practice_plan.rotations
        .select_related(
            'assigned_coach',
            'testing_session',
        )
        .prefetch_related(
            'stations',
        )
        .order_by(
            'order',
        )
    )

    athlete_assignments = (
        practice_plan.athlete_assignments
        .select_related(
            'athlete',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )

    testing_sessions = (
        practice_plan.testing_sessions
        .prefetch_related(
            'exercises',
            'athletes',
        )
        .order_by(
            'testing_date',
        )
    )

    total_rotation_minutes = sum(
        rotation.duration_minutes
        for rotation in rotations
    )

    context = {
        'practice_plan': practice_plan,
        'rotations': rotations,
        'athlete_assignments': athlete_assignments,
        'testing_sessions': testing_sessions,
        'total_rotation_minutes': (
            total_rotation_minutes
        ),
        'remaining_minutes': max(
            practice_plan.duration_minutes
            - total_rotation_minutes,
            0,
        ),
    }

    return render(
        request,
        'practice_planner/practice_detail.html',
        context,
    )


@login_required
def practice_update(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    previous_group_id = (
        practice_plan.training_group_id
    )

    if request.method == 'POST':
        form = PracticePlanForm(
            request.POST,
            instance=practice_plan,
            user=request.user,
        )

        if form.is_valid():
            with transaction.atomic():
                practice_plan = form.save()

                if (
                        previous_group_id
                        != practice_plan.training_group_id
                ):
                    practice_plan.athlete_assignments.all().delete()

                    create_default_athlete_assignments(
                        practice_plan
                    )

            messages.success(
                request,
                (
                    f'Practice "{practice_plan.title}" '
                    f'was updated.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticePlanForm(
            instance=practice_plan,
            user=request.user,
        )

    context = {
        'form': form,
        'practice_plan': practice_plan,
        'page_title': 'Edit Practice',
        'submit_label': 'Save Changes',
    }

    return render(
        request,
        'practice_planner/practice_form.html',
        context,
    )


@login_required
def practice_builder(
    request,
    practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    rotations = list(
        practice_plan.rotations
        .select_related(
            'assigned_coach',
            'testing_session',
        )
        .prefetch_related(
            'stations',
            'testing_session__exercises',
            'testing_session__athletes',
        )
        .order_by(
            'order',
        )
    )

    athlete_assignments = list(
        practice_plan.athlete_assignments
        .select_related(
            'athlete',
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username',
        )
    )

    total_rotation_minutes = sum(
        rotation.duration_minutes
        for rotation in rotations
    )

    practice_minutes = (
        practice_plan.duration_minutes
    )

    remaining_minutes = max(
        practice_minutes
        - total_rotation_minutes,
        0,
    )

    over_minutes = max(
        total_rotation_minutes
        - practice_minutes,
        0,
    )

    if practice_minutes > 0:
        planned_percentage = round(
            (
                total_rotation_minutes
                / practice_minutes
            )
            * 100
        )
    else:
        planned_percentage = 0

    display_percentage = min(
        planned_percentage,
        100,
    )

    modified_athletes = [
        assignment
        for assignment in athlete_assignments
        if assignment.workload
        != PracticeAthleteAssignment.WORKLOAD_FULL
        or not assignment.is_expected
        or assignment.restrictions
    ]

    context = {
        'practice_plan': practice_plan,
        'rotations': rotations,
        'athlete_assignments': athlete_assignments,
        'modified_athletes': modified_athletes,
        'total_rotation_minutes': (
            total_rotation_minutes
        ),
        'remaining_minutes': remaining_minutes,
        'over_minutes': over_minutes,
        'planned_percentage': planned_percentage,
        'display_percentage': display_percentage,
    }

    return render(
        request,
        'practice_planner/practice_builder.html',
        context,
    )

@login_required
def rotation_create(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    next_order = (
            practice_plan.rotations.count()
            + 1
    )

    if request.method == 'POST':
        form = PracticeRotationForm(
            request.POST,
            practice_plan=practice_plan,
            user=request.user,
        )

        if form.is_valid():
            rotation = form.save()

            messages.success(
                request,
                (
                    f'Rotation "{rotation.title}" '
                    f'was added.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticeRotationForm(
            practice_plan=practice_plan,
            user=request.user,
            initial={
                'order': next_order,
            },
        )

    context = {
        'form': form,
        'practice_plan': practice_plan,
        'page_title': 'Add Rotation',
        'submit_label': 'Add Rotation',
    }

    return render(
        request,
        'practice_planner/rotation_form.html',
        context,
    )


@login_required
def rotation_update(
        request,
        rotation_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    rotation = get_object_or_404(
        PracticeRotation.objects.select_related(
            'practice_plan',
            'practice_plan__training_group',
            'testing_session',
        ),
        id=rotation_id,
    )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    if request.method == 'POST':
        form = PracticeRotationForm(
            request.POST,
            instance=rotation,
            practice_plan=practice_plan,
            user=request.user,
        )

        if form.is_valid():
            rotation = form.save()

            messages.success(
                request,
                (
                    f'Rotation "{rotation.title}" '
                    f'was updated.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticeRotationForm(
            instance=rotation,
            practice_plan=practice_plan,
            user=request.user,
        )

    context = {
        'form': form,
        'rotation': rotation,
        'practice_plan': practice_plan,
        'page_title': 'Edit Rotation',
        'submit_label': 'Save Rotation',
    }

    return render(
        request,
        'practice_planner/rotation_form.html',
        context,
    )


@login_required
def rotation_delete(
        request,
        rotation_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    rotation = get_object_or_404(
        PracticeRotation.objects.select_related(
            'practice_plan',
        ),
        id=rotation_id,
    )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    if request.method == 'POST':
        rotation_title = rotation.title

        rotation.delete()

        reorder_practice_rotations(
            practice_plan
        )

        messages.success(
            request,
            (
                f'Rotation "{rotation_title}" '
                f'was removed.'
            ),
        )

        return redirect(
            'practice_planner:practice_builder',
            practice_id=practice_plan.id,
        )

    context = {
        'rotation': rotation,
        'practice_plan': practice_plan,
    }

    return render(
        request,
        'practice_planner/rotation_confirm_delete.html',
        context,
    )


@login_required
def station_create(
        request,
        rotation_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    rotation = get_object_or_404(
        PracticeRotation.objects.select_related(
            'practice_plan',
        ),
        id=rotation_id,
    )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    if rotation.is_testing_rotation:
        messages.warning(
            request,
            (
                'Testing exercises must be managed through '
                'the linked Performance Testing session.'
            ),
        )

        return redirect(
            'practice_planner:practice_builder',
            practice_id=practice_plan.id,
        )

    next_order = (
            rotation.stations.count()
            + 1
    )

    if request.method == 'POST':
        form = PracticeStationForm(
            request.POST,
            rotation=rotation,
        )

        if form.is_valid():
            station = form.save()

            messages.success(
                request,
                (
                    f'Station "{station.title}" '
                    f'was added.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticeStationForm(
            rotation=rotation,
            initial={
                'order': next_order,
            },
        )

    context = {
        'form': form,
        'rotation': rotation,
        'practice_plan': practice_plan,
        'page_title': 'Add Station',
        'submit_label': 'Add Station',
    }

    return render(
        request,
        'practice_planner/station_form.html',
        context,
    )


@login_required
def station_update(
        request,
        station_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    station = get_object_or_404(
        PracticeStation.objects.select_related(
            'rotation',
            'rotation__practice_plan',
        ),
        id=station_id,
    )

    rotation = station.rotation

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    if request.method == 'POST':
        form = PracticeStationForm(
            request.POST,
            instance=station,
            rotation=rotation,
        )

        if form.is_valid():
            station = form.save()

            messages.success(
                request,
                (
                    f'Station "{station.title}" '
                    f'was updated.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticeStationForm(
            instance=station,
            rotation=rotation,
        )

    context = {
        'form': form,
        'station': station,
        'rotation': rotation,
        'practice_plan': practice_plan,
        'page_title': 'Edit Station',
        'submit_label': 'Save Station',
    }

    return render(
        request,
        'practice_planner/station_form.html',
        context,
    )


@login_required
def station_delete(
        request,
        station_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    station = get_object_or_404(
        PracticeStation.objects.select_related(
            'rotation',
            'rotation__practice_plan',
        ),
        id=station_id,
    )

    rotation = station.rotation

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    if request.method == 'POST':
        station_title = station.title

        station.delete()

        reorder_rotation_stations(
            rotation
        )

        messages.success(
            request,
            (
                f'Station "{station_title}" '
                f'was removed.'
            ),
        )

        return redirect(
            'practice_planner:practice_builder',
            practice_id=practice_plan.id,
        )

    context = {
        'station': station,
        'rotation': rotation,
        'practice_plan': practice_plan,
    }

    return render(
        request,
        'practice_planner/station_confirm_delete.html',
        context,
    )


@login_required
def athlete_assignment_update(
        request,
        assignment_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    assignment = get_object_or_404(
        PracticeAthleteAssignment.objects.select_related(
            'practice_plan',
            'athlete',
        ),
        id=assignment_id,
    )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=assignment.practice_plan_id,
    )

    if request.method == 'POST':
        form = PracticeAthleteAssignmentForm(
            request.POST,
            instance=assignment,
            practice_plan=practice_plan,
        )

        if form.is_valid():
            assignment = form.save()

            messages.success(
                request,
                (
                    f'Training plan for '
                    f'{assignment.athlete.username} '
                    f'was updated.'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = PracticeAthleteAssignmentForm(
            instance=assignment,
            practice_plan=practice_plan,
        )

    context = {
        'form': form,
        'assignment': assignment,
        'practice_plan': practice_plan,
        'page_title': 'Edit Athlete Training Plan',
        'submit_label': 'Save Athlete Plan',
    }

    return render(
        request,
        'practice_planner/athlete_assignment_form.html',
        context,
    )


@login_required
def create_testing_session_for_practice(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    testing_session = TestingSession.objects.create(
        title=(
            f'{practice_plan.training_group.name} '
            f'Practice Testing'
        ),
        testing_date=practice_plan.practice_date,
        training_group=practice_plan.training_group,
        practice_plan=practice_plan,
        created_by=request.user,
        status=TestingSession.STATUS_DRAFT,
    )

    testing_session.copy_group_athletes()

    messages.success(
        request,
        (
            'A draft Performance Testing session was created. '
            'Add exercises before attaching it to a rotation.'
        ),
    )

    return redirect(
        'performance_testing:session_update',
        session_id=testing_session.id,
    )


@login_required
def practice_start(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    if request.method != 'POST':
        return redirect(
            'practice_planner:practice_detail',
            practice_id=practice_plan.id,
        )

    if not practice_plan.rotations.exists():
        messages.error(
            request,
            'Add at least one rotation before starting practice.',
        )

        return redirect(
            'practice_planner:practice_builder',
            practice_id=practice_plan.id,
        )

    practice_plan.status = (
        PracticePlan.STATUS_IN_PROGRESS
    )

    practice_plan.started_at = (
        timezone.now()
    )

    practice_plan.save(
        update_fields=[
            'status',
            'started_at',
            'updated_at',
        ],
    )

    messages.success(
        request,
        (
            f'Practice "{practice_plan.title}" '
            f'has started.'
        ),
    )

    return redirect(
        'practice_planner:practice_detail',
        practice_id=practice_plan.id,
    )


@login_required
def practice_complete(
        request,
        practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    if request.method != 'POST':
        return redirect(
            'practice_planner:practice_detail',
            practice_id=practice_plan.id,
        )

    practice_plan.status = (
        PracticePlan.STATUS_COMPLETED
    )

    practice_plan.completed_at = (
        timezone.now()
    )

    practice_plan.save(
        update_fields=[
            'status',
            'completed_at',
            'updated_at',
        ],
    )

    practice_plan.testing_sessions.filter(
        status=TestingSession.STATUS_IN_PROGRESS,
    ).update(
        status=TestingSession.STATUS_COMPLETED,
    )

    messages.success(
        request,
        (
            f'Practice "{practice_plan.title}" '
            f'was marked complete.'
        ),
    )

    return redirect(
        'practice_planner:practice_detail',
        practice_id=practice_plan.id,
    )


def create_default_athlete_assignments(
        practice_plan,
):
    """
    Create one default practice assignment for every active athlete
    in the selected training group.
    """

    athletes = (
        practice_plan.training_group
        .athletes
        .filter(
            role='athlete',
            is_active=True,
        )
    )

    assignments = [
        PracticeAthleteAssignment(
            practice_plan=practice_plan,
            athlete=athlete,
            workload=(
                PracticeAthleteAssignment.WORKLOAD_FULL
            ),
            is_expected=True,
        )
        for athlete in athletes
    ]

    PracticeAthleteAssignment.objects.bulk_create(
        assignments,
        ignore_conflicts=True,
    )


def reorder_practice_rotations(
        practice_plan,
):
    """
    Reset rotation order after one rotation has been removed.
    """

    rotations = (
        practice_plan.rotations
        .order_by(
            'order',
            'id',
        )
    )

    for index, rotation in enumerate(
            rotations,
            start=1,
    ):
        if rotation.order != index:
            rotation.order = index

            rotation.save(
                update_fields=[
                    'order',
                ],
            )


def reorder_rotation_stations(
        rotation,
):
    """
    Reset station order after one station has been removed.
    """

    stations = (
        rotation.stations
        .order_by(
            'order',
            'id',
        )
    )

    for index, station in enumerate(
            stations,
            start=1,
    ):
        if station.order != index:
            station.order = index

            station.save(
                update_fields=[
                    'order',
                ],
            )

@login_required
@require_POST
def reorder_rotations(
    request,
    practice_id,
):
    """
    Save a new drag-and-drop order for a practice's rotations.
    """

    if not user_is_coach(request.user):
        return JsonResponse(
            {
                'success': False,
                'error': 'You do not have permission to edit this practice.',
            },
            status=403,
        )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=practice_id,
    )

    try:
        payload = json.loads(
            request.body.decode('utf-8')
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Invalid request data.',
            },
            status=400,
        )

    rotation_ids = payload.get(
        'rotation_ids',
        [],
    )

    try:
        rotation_ids = [
            int(rotation_id)
            for rotation_id in rotation_ids
        ]
    except (
        TypeError,
        ValueError,
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Invalid rotation IDs.',
            },
            status=400,
        )

    existing_rotations = list(
        practice_plan.rotations.order_by(
            'order',
            'id',
        )
    )

    existing_ids = {
        rotation.id
        for rotation in existing_rotations
    }

    submitted_ids = set(
        rotation_ids
    )

    if (
        existing_ids != submitted_ids
        or len(rotation_ids) != len(submitted_ids)
    ):
        return JsonResponse(
            {
                'success': False,
                'error': (
                    'The submitted rotation list does not '
                    'match this practice.'
                ),
            },
            status=400,
        )

    rotation_map = {
        rotation.id: rotation
        for rotation in existing_rotations
    }

    with transaction.atomic():
        max_order = max(
            (
                rotation.order
                for rotation in existing_rotations
            ),
            default=0,
        )

        temporary_start = (
            max_order
            + len(existing_rotations)
            + 100
        )

        for temporary_index, rotation_id in enumerate(
            rotation_ids,
            start=1,
        ):
            rotation = rotation_map[
                rotation_id
            ]

            rotation.order = (
                temporary_start
                + temporary_index
            )

            rotation.save(
                update_fields=[
                    'order',
                ],
            )

        for final_order, rotation_id in enumerate(
            rotation_ids,
            start=1,
        ):
            rotation = rotation_map[
                rotation_id
            ]

            rotation.order = final_order

            rotation.save(
                update_fields=[
                    'order',
                ],
            )

    return JsonResponse({
        'success': True,
        'message': 'Rotation order saved.',
    })
def copy_practice_to_template(
    practice_plan,
    practice_template,
):
    """
    Copy a practice's rotations and stations into a reusable template.
    """

    rotations = (
        practice_plan.rotations
        .prefetch_related(
            'stations',
        )
        .order_by(
            'order',
        )
    )

    for rotation in rotations:
        template_rotation = (
            PracticeTemplateRotation.objects.create(
                template=practice_template,
                title=rotation.title,
                event=rotation.event,
                order=rotation.order,
                duration_minutes=(
                    rotation.duration_minutes
                ),
                location=rotation.location,
                objective=rotation.objective,
                coach_notes=rotation.coach_notes,
                include_testing=(
                    rotation.is_testing_rotation
                ),
            )
        )

        if rotation.is_testing_rotation:
            continue

        template_stations = []

        for station in rotation.stations.order_by(
            'order',
        ):
            template_stations.append(
                PracticeTemplateStation(
                    template_rotation=(
                        template_rotation
                    ),
                    title=station.title,
                    station_type=(
                        station.station_type
                    ),
                    order=station.order,
                    duration_minutes=(
                        station.duration_minutes
                    ),
                    sets=station.sets,
                    repetitions=(
                        station.repetitions
                    ),
                    target_attempts=(
                        station.target_attempts
                    ),
                    instructions=(
                        station.instructions
                    ),
                    coaching_cues=(
                        station.coaching_cues
                    ),
                    equipment=station.equipment,
                    success_criteria=(
                        station.success_criteria
                    ),
                    reference_video_url=(
                        station.reference_video_url
                    ),
                    is_optional=(
                        station.is_optional
                    ),
                )
            )

        PracticeTemplateStation.objects.bulk_create(
            template_stations
        )

@login_required
@require_POST
def reorder_stations(
    request,
    rotation_id,
):
    """
    Save a new drag-and-drop order for a rotation's stations.
    """

    if not user_is_coach(request.user):
        return JsonResponse(
            {
                'success': False,
                'error': 'You do not have permission to edit this rotation.',
            },
            status=403,
        )

    rotation = get_object_or_404(
        PracticeRotation.objects.select_related(
            'practice_plan',
        ),
        id=rotation_id,
    )

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ),
        id=rotation.practice_plan_id,
    )

    try:
        payload = json.loads(
            request.body.decode('utf-8')
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Invalid request data.',
            },
            status=400,
        )

    station_ids = payload.get(
        'station_ids',
        [],
    )

    try:
        station_ids = [
            int(station_id)
            for station_id in station_ids
        ]
    except (
        TypeError,
        ValueError,
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Invalid station IDs.',
            },
            status=400,
        )

    existing_stations = list(
        rotation.stations.order_by(
            'order',
            'id',
        )
    )

    existing_ids = {
        station.id
        for station in existing_stations
    }

    submitted_ids = set(
        station_ids
    )

    if (
        existing_ids != submitted_ids
        or len(station_ids) != len(submitted_ids)
    ):
        return JsonResponse(
            {
                'success': False,
                'error': (
                    'The submitted station list does not '
                    'match this rotation.'
                ),
            },
            status=400,
        )

    station_map = {
        station.id: station
        for station in existing_stations
    }

    with transaction.atomic():
        max_order = max(
            (
                station.order
                for station in existing_stations
            ),
            default=0,
        )

        temporary_start = (
            max_order
            + len(existing_stations)
            + 100
        )

        for temporary_index, station_id in enumerate(
            station_ids,
            start=1,
        ):
            station = station_map[
                station_id
            ]

            station.order = (
                temporary_start
                + temporary_index
            )

            station.save(
                update_fields=[
                    'order',
                ],
            )

        for final_order, station_id in enumerate(
            station_ids,
            start=1,
        ):
            station = station_map[
                station_id
            ]

            station.order = final_order

            station.save(
                update_fields=[
                    'order',
                ],
            )

    return JsonResponse({
        'success': True,
        'message': 'Station order saved.',
        'practice_id': practice_plan.id,
    })


from django.shortcuts import render


@login_required
def save_practice_as_template(
    request,
    practice_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_plan = get_object_or_404(
        get_accessible_practices(
            request.user
        ).select_related(
            'training_group',
        ).prefetch_related(
            'rotations__stations',
        ),
        id=practice_id,
    )

    if request.method == 'POST':
        form = SavePracticeTemplateForm(
            request.POST,
            user=request.user,
            practice_plan=practice_plan,
        )

        if form.is_valid():
            with transaction.atomic():
                practice_template = form.save(
                    commit=False,
                )

                practice_template.created_by = (
                    request.user
                )

                practice_template.source_practice = (
                    practice_plan
                )

                practice_template.planned_intensity = (
                    practice_plan.planned_intensity
                )

                practice_template.primary_focus = (
                    practice_plan.primary_focus
                )

                practice_template.coach_objectives = (
                    practice_plan.coach_objectives
                )

                practice_template.general_notes = (
                    practice_plan.general_notes
                )

                practice_template.default_duration_minutes = (
                    practice_plan.duration_minutes
                )

                practice_template.save()

                copy_practice_to_template(
                    practice_plan=practice_plan,
                    practice_template=practice_template,
                )

            messages.success(
                request,
                (
                    f'Practice "{practice_plan.title}" '
                    f'was saved as template '
                    f'"{practice_template.name}".'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = SavePracticeTemplateForm(
            user=request.user,
            practice_plan=practice_plan,
        )

    context = {
        'form': form,
        'practice_plan': practice_plan,
        'page_title': 'Save Practice as Template',
        'submit_label': 'Save Template',
    }

    return render(
        request,
        'practice_planner/save_template_form.html',
        context,
    )
@login_required
def create_practice_from_template(
    request,
    template_id,
):
    if not user_is_coach(request.user):
        return coach_access_denied(request)

    practice_template = get_object_or_404(
        PracticeTemplate.objects
        .select_related(
            'created_by',
        )
        .prefetch_related(
            'rotations__stations',
        )
        .filter(
            Q(created_by=request.user)
            | Q(is_shared=True)
        ),
        id=template_id,
        is_active=True,
    )

    if request.method == 'POST':
        form = CreatePracticeFromTemplateForm(
            request.POST,
            user=request.user,
            practice_template=practice_template,
        )

        if form.is_valid():
            with transaction.atomic():
                practice_plan = (
                    PracticePlan.objects.create(
                        title=(
                            form.cleaned_data[
                                'title'
                            ]
                        ),
                        practice_date=(
                            form.cleaned_data[
                                'practice_date'
                            ]
                        ),
                        start_time=(
                            form.cleaned_data[
                                'start_time'
                            ]
                        ),
                        end_time=(
                            form.cleaned_data[
                                'end_time'
                            ]
                        ),
                        training_group=(
                            form.cleaned_data[
                                'training_group'
                            ]
                        ),
                        lead_coach=(
                            form.cleaned_data[
                                'lead_coach'
                            ]
                        ),
                        status=(
                            form.cleaned_data[
                                'status'
                            ]
                        ),
                        planned_intensity=(
                            form.cleaned_data[
                                'planned_intensity'
                            ]
                        ),
                        primary_focus=(
                            form.cleaned_data[
                                'primary_focus'
                            ]
                        ),
                        coach_objectives=(
                            form.cleaned_data[
                                'coach_objectives'
                            ]
                        ),
                        general_notes=(
                            form.cleaned_data[
                                'general_notes'
                            ]
                        ),
                        created_by=request.user,
                    )
                )

                practice_plan.assistant_coaches.set(
                    form.cleaned_data[
                        'assistant_coaches'
                    ]
                )

                copy_template_to_practice(
                    practice_template=practice_template,
                    practice_plan=practice_plan,
                    target_duration_minutes=(
                        form.cleaned_data[
                            'target_duration_minutes'
                        ]
                    ),
                    scale_durations=(
                        form.cleaned_data[
                            'scale_rotation_durations'
                        ]
                    ),
                    include_testing=(
                        form.cleaned_data[
                            'include_testing_rotations'
                        ]
                    ),
                    include_optional=(
                        form.cleaned_data[
                            'include_optional_rotations'
                        ]
                    ),
                )

                create_default_athlete_assignments(
                    practice_plan
                )

                PracticeTemplate.objects.filter(
                    id=practice_template.id,
                ).update(
                    times_used=(
                        practice_template.times_used
                        + 1
                    )
                )

            messages.success(
                request,
                (
                    f'Practice "{practice_plan.title}" '
                    f'was created from template '
                    f'"{practice_template.name}".'
                ),
            )

            return redirect(
                'practice_planner:practice_builder',
                practice_id=practice_plan.id,
            )

    else:
        form = CreatePracticeFromTemplateForm(
            user=request.user,
            practice_template=practice_template,
        )

    template_rotations = list(
        practice_template.rotations
        .order_by(
            'order',
        )
        .values(
            'id',
            'title',
            'event',
            'duration_minutes',
            'include_testing',
            'is_optional',
        )
    )

    context = {
        'form': form,
        'practice_template': practice_template,
        'template_rotations': template_rotations,
        'page_title': (
            'Create Practice from Template'
        ),
        'submit_label': 'Create Practice',
    }

    return render(
        request,
        (
            'practice_planner/'
            'create_from_template_form.html'
        ),
        context,
    )

def calculate_scaled_rotation_durations(
    rotations,
    target_minutes,
):
    """
    Proportionally scale rotation durations so their final
    total exactly matches the requested practice length.
    """

    original_total = sum(
        rotation.duration_minutes
        for rotation in rotations
    )

    if original_total <= 0:
        return {
            rotation.id: 1
            for rotation in rotations
        }

    raw_durations = []

    for rotation in rotations:
        raw_duration = (
            rotation.duration_minutes
            / original_total
            * target_minutes
        )

        base_duration = max(
            1,
            int(raw_duration),
        )

        raw_durations.append({
            'rotation': rotation,
            'duration': base_duration,
            'remainder': (
                raw_duration
                - int(raw_duration)
            ),
        })

    current_total = sum(
        item['duration']
        for item in raw_durations
    )

    difference = (
        target_minutes
        - current_total
    )

    if difference > 0:
        ranked_items = sorted(
            raw_durations,
            key=lambda item: item['remainder'],
            reverse=True,
        )

        index = 0

        while difference > 0:
            item = ranked_items[
                index % len(ranked_items)
            ]

            item['duration'] += 1

            difference -= 1
            index += 1

    elif difference < 0:
        ranked_items = sorted(
            raw_durations,
            key=lambda item: item['remainder'],
        )

        index = 0
        attempts = 0

        maximum_attempts = (
            abs(difference)
            * len(ranked_items)
            * 2
            + 100
        )

        while (
            difference < 0
            and attempts < maximum_attempts
        ):
            item = ranked_items[
                index % len(ranked_items)
            ]

            if item['duration'] > 1:
                item['duration'] -= 1
                difference += 1

            index += 1
            attempts += 1

    return {
        item['rotation'].id: item['duration']
        for item in raw_durations
    }


def copy_template_to_practice(
    practice_template,
    practice_plan,
    target_duration_minutes,
    scale_durations=True,
    include_testing=True,
    include_optional=True,
):
    """
    Copy template rotations and stations into a new practice.

    Rotation durations can be proportionally adjusted to match
    the new scheduled practice length.
    """

    template_rotations = list(
        practice_template.rotations
        .prefetch_related(
            'stations',
        )
        .order_by(
            'order',
        )
    )

    if not include_testing:
        template_rotations = [
            rotation
            for rotation in template_rotations
            if not rotation.include_testing
        ]

    if not include_optional:
        template_rotations = [
            rotation
            for rotation in template_rotations
            if not rotation.is_optional
        ]

    if not template_rotations:
        return

    original_total_minutes = sum(
        rotation.duration_minutes
        for rotation in template_rotations
    )

    if (
        scale_durations
        and original_total_minutes > 0
    ):
        scaled_durations = (
            calculate_scaled_rotation_durations(
                rotations=template_rotations,
                target_minutes=target_duration_minutes,
            )
        )

    else:
        scaled_durations = {
            rotation.id: rotation.duration_minutes
            for rotation in template_rotations
        }

    for new_order, template_rotation in enumerate(
        template_rotations,
        start=1,
    ):
        practice_rotation = (
            PracticeRotation.objects.create(
                practice_plan=practice_plan,
                title=template_rotation.title,
                event=template_rotation.event,
                order=new_order,
                duration_minutes=(
                    scaled_durations[
                        template_rotation.id
                    ]
                ),
                location=template_rotation.location,
                objective=template_rotation.objective,
                coach_notes=template_rotation.coach_notes,
                is_testing_rotation=(
                    template_rotation.include_testing
                ),
            )
        )

        if template_rotation.include_testing:
            continue

        stations = []

        for template_station in (
            template_rotation.stations
            .order_by(
                'order',
            )
        ):
            stations.append(
                PracticeStation(
                    rotation=practice_rotation,
                    title=template_station.title,
                    station_type=(
                        template_station.station_type
                    ),
                    order=template_station.order,
                    duration_minutes=(
                        template_station.duration_minutes
                    ),
                    sets=template_station.sets,
                    repetitions=(
                        template_station.repetitions
                    ),
                    target_attempts=(
                        template_station.target_attempts
                    ),
                    instructions=(
                        template_station.instructions
                    ),
                    coaching_cues=(
                        template_station.coaching_cues
                    ),
                    equipment=template_station.equipment,
                    success_criteria=(
                        template_station.success_criteria
                    ),
                    reference_video_url=(
                        template_station.reference_video_url
                    ),
                    is_optional=(
                        template_station.is_optional
                    ),
                )
            )

        PracticeStation.objects.bulk_create(
            stations
        )
