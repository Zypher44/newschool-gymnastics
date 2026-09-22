from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .forms import (
    AthletePathwayForm,
)

from .forms_routines import (
    AthleteRoutineElementForm,
)

from parents_portal.access import get_approved_parent_links

from .models import (
    AthletePathway,
    AthletePathwayRequirement,
    AthleteRoutine,
    AthleteRoutineElement,
    AthleteRoutineRequirement,
    PathwayEvent,
    PathwayLevel,
    PathwayRequirement,

)

from .routine_services import (
    calculate_beam_d_score,
    calculate_routine_d_score,
    sync_routine_requirements,
    update_element_difficulty_value,
)

from .services import (
    sync_athlete_pathway_requirements,
)
from .routine_services import (
    calculate_beam_d_score,
    calculate_floor_d_score,
    calculate_routine_d_score,
    calculate_vault_d_score,
    sync_routine_requirements,
    update_element_difficulty_value,
)

User = get_user_model()


# ============================================================
# PERMISSION HELPERS
# ============================================================


def is_head_coach(
    user,
):
    return (
        user.is_authenticated
        and
        user.role == 'head_coach'
    )


def is_coach(
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


def can_view_pathway(
    user,
):
    return (
        user.is_authenticated
        and
        user.role in [
            'coach',
            'head_coach',
            'athlete',
            'parent',
        ]
    )


def hp_scoring_only(view):
    """Do not apply the existing HP calculator to an optional pathway."""
    @wraps(view)
    def wrapped(request, athlete_id, *args, **kwargs):
        if is_coach(request.user):
            pathway = (
                AthletePathway.objects
                .select_related('current_level', 'target_level')
                .filter(athlete_id=athlete_id).first()
            )
            if pathway and pathway.has_usag_optional_level:
                messages.info(
                    request,
                    'USAG optional pathways use different start-value rules. '
                    'Use the coach-assessed checklist; the HP D-score calculator '
                    'does not calculate USAG optional scores.',
                )
                return redirect('pathway:athlete_pathway_requirements', athlete_id=athlete_id)
        return view(request, athlete_id, *args, **kwargs)
    return wrapped


# ============================================================
# HEAD COACH PATHWAY MANAGER
# ============================================================


@login_required
def pathway_manager(
    request,
):
    if not is_head_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only head coaches can '
                'manage athlete pathways.'
            ),
        )

        return redirect(
            'role_redirect'
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


    pathways = (
        AthletePathway.objects
        .select_related(
            'athlete',
            'current_level',
            'target_level',
            'managed_by',
        )
    )


    pathway_lookup = {
        pathway.athlete_id: pathway
        for pathway
        in pathways
    }


    athlete_rows = []


    for athlete in athletes:

        athlete_rows.append({
            'athlete': athlete,

            'pathway': (
                pathway_lookup.get(
                    athlete.id
                )
            ),
        })


    levels = (
        PathwayLevel.objects
        .filter(
            is_active=True,
        )
        .order_by(
            'order',
        )
    )


    context = {
        'athlete_rows': (
            athlete_rows
        ),

        'levels': levels,

        'athlete_count': (
            len(
                athlete_rows
            )
        ),

        'pathway_count': (
            len(
                pathway_lookup
            )
        ),
    }


    return render(
        request,
        'pathway/pathway_manager.html',
        context,
    )


# ============================================================
# ATHLETE PATHWAY SETUP
# ============================================================


@login_required
def athlete_pathway_editor(
    request,
    athlete_id,
):
    if not is_head_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only head coaches can '
                'manage athlete pathways.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway, created = (
        AthletePathway.objects
        .get_or_create(
            athlete=athlete,

            defaults={
                'managed_by': (
                    request.user
                ),
            },
        )
    )


    if request.method == 'POST':

        form = AthletePathwayForm(
            request.POST,
            instance=athlete_pathway,
        )


        if form.is_valid():

            athlete_pathway = (
                form.save(
                    commit=False
                )
            )

            athlete_pathway.managed_by = (
                request.user
            )

            athlete_pathway.save()


            sync_results = (
                sync_athlete_pathway_requirements(
                    athlete_pathway
                )
            )


            messages.success(
                request,
                (
                    'Athlete pathway updated. '
                    f'{sync_results["created"]} '
                    'new pathway requirements '
                    'were added.'
                ),
            )


            return redirect(
                'pathway:athlete_pathway_editor',
                athlete_id=athlete.id,
            )


    else:

        form = AthletePathwayForm(
            instance=athlete_pathway,
        )


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'form': form,
    }


    return render(
        request,
        'pathway/athlete_pathway_editor.html',
        context,
    )


# ============================================================
# ATHLETE SKILL TREE
# ============================================================


@login_required
def athlete_pathway_requirements(
    request,
    athlete_id,
):
    if not is_head_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only head coaches can '
                'manage athlete pathways.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = get_object_or_404(
        AthletePathway.objects
        .select_related(
            'athlete',
            'current_level',
            'target_level',
            'managed_by',
        ),
        athlete=athlete,
    )


    sync_athlete_pathway_requirements(
        athlete_pathway
    )


    selected_levels = []

    if athlete_pathway.current_level_id:
        selected_levels.append({
            'level': athlete_pathway.current_level,
            'label': 'Current Level',
        })

    if athlete_pathway.target_level_id:
        if (
            athlete_pathway.target_level_id
            == athlete_pathway.current_level_id
        ):
            selected_levels[0]['label'] = (
                'Current & Target Level'
            )
        else:
            selected_levels.append({
                'level': athlete_pathway.target_level,
                'label': 'Target Level',
            })

    selected_level_ids = [
        item['level'].id
        for item in selected_levels
    ]


    athlete_requirements = list(
        AthletePathwayRequirement.objects
        .filter(
            athlete_pathway=(
                athlete_pathway
            ),
            requirement__is_active=True,
            requirement__level_id__in=(
                selected_level_ids
            ),
        )
        .select_related(
            'requirement',
            'requirement__level',
            'requirement__event',
            'updated_by',
        )
        .order_by(
            'requirement__event__order',
            'requirement__level__order',
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )


    level_progress = []


    for selected_level in selected_levels:
        level = selected_level['level']

        level_required_items = [
            item
            for item in athlete_requirements
            if (
                item.requirement.level_id
                == level.id
                and item.requirement.is_required
            )
        ]

        level_completed_items = [
            item
            for item in level_required_items
            if (
                item.status
                == AthletePathwayRequirement
                .STATUS_COMPETITION_READY
            )
        ]

        level_required_count = len(
            level_required_items
        )

        level_completed_count = len(
            level_completed_items
        )

        if level_required_count:
            level_percentage = round(
                (
                    level_completed_count
                    / level_required_count
                )
                * 100
            )
        else:
            level_percentage = 0

        level_progress.append({
            'level': level,
            'label': selected_level['label'],
            'required_count': level_required_count,
            'completed_count': level_completed_count,
            'completion_percentage': level_percentage,
        })


    events = (
        PathwayEvent.objects
        .all()
        .order_by(
            'order',
        )
    )


    event_sections = []


    for event in events:

        event_requirements = [
            athlete_requirement
            for athlete_requirement
            in athlete_requirements
            if (
                athlete_requirement
                .requirement
                .event_id
                ==
                event.id
            )
        ]


        if not event_requirements:
            continue


        required_items = [
            item
            for item
            in event_requirements
            if item.requirement.is_required
        ]


        completed_items = [
            item
            for item
            in required_items
            if (
                item.status
                ==
                AthletePathwayRequirement
                .STATUS_COMPETITION_READY
            )
        ]


        required_count = len(
            required_items
        )

        completed_count = len(
            completed_items
        )


        if required_count:

            completion_percentage = round(
                (
                    completed_count
                    /
                    required_count
                )
                * 100
            )

        else:

            completion_percentage = 0


        event_sections.append({
            'event': event,

            'requirements': (
                event_requirements
            ),

            'required_count': (
                required_count
            ),

            'completed_count': (
                completed_count
            ),

            'completion_percentage': (
                completion_percentage
            ),
        })


    total_required = sum(
        section[
            'required_count'
        ]
        for section
        in event_sections
    )


    total_completed = sum(
        section[
            'completed_count'
        ]
        for section
        in event_sections
    )


    if total_required:

        overall_percentage = round(
            (
                total_completed
                /
                total_required
            )
            * 100
        )

    else:

        overall_percentage = 0


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'event_sections': (
            event_sections
        ),

        'overall_percentage': (
            overall_percentage
        ),

        'level_progress': (
            level_progress
        ),

        'total_required': (
            total_required
        ),

        'total_completed': (
            total_completed
        ),

        'status_choices': (
            AthletePathwayRequirement
            .STATUS_CHOICES
        ),
    }


    return render(
        request,
        'pathway/athlete_pathway_requirements.html',
        context,
    )


# ============================================================
# SINGLE REQUIREMENT UPDATE
# ============================================================


@login_required
@require_POST
def update_athlete_pathway_requirement(
    request,
    requirement_id,
):
    if not is_head_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only head coaches can '
                'update pathway requirements.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete_requirement = get_object_or_404(
        AthletePathwayRequirement.objects
        .select_related(
            'athlete_pathway',
            'athlete_pathway__athlete',
            'requirement',
        ),
        id=requirement_id,
    )


    status = (
        request.POST.get(
            'status',
            '',
        )
        .strip()
    )


    coach_note = (
        request.POST.get(
            'coach_note',
            '',
        )
        .strip()
    )


    target_date = (
        request.POST.get(
            'target_date',
            '',
        )
        .strip()
    )


    hide_from_parent = (
        request.POST.get(
            'is_hidden_from_parent'
        )
        == 'yes'
    )


    allowed_statuses = {
        choice[0]
        for choice
        in (
            AthletePathwayRequirement
            .STATUS_CHOICES
        )
    }


    if status not in allowed_statuses:

        messages.error(
            request,
            (
                'Choose a valid '
                'requirement status.'
            ),
        )

        return redirect(
            'pathway:athlete_pathway_requirements',
            athlete_id=(
                athlete_requirement
                .athlete_pathway
                .athlete_id
            ),
        )


    athlete_requirement.status = (
        status
    )

    athlete_requirement.coach_note = (
        coach_note
    )

    athlete_requirement.target_date = (
        target_date
        or None
    )

    athlete_requirement.is_hidden_from_parent = (
        hide_from_parent
    )

    athlete_requirement.updated_by = (
        request.user
    )


    athlete_requirement.save(
        update_fields=[
            'status',
            'coach_note',
            'target_date',
            'is_hidden_from_parent',
            'updated_by',
            'updated_at',
        ],
    )


    messages.success(
        request,
        (
            f'{athlete_requirement.requirement.title} '
            'was updated.'
        ),
    )


    return redirect(
        'pathway:athlete_pathway_requirements',
        athlete_id=(
            athlete_requirement
            .athlete_pathway
            .athlete_id
        ),
    )


# ============================================================
# BULK SKILL TREE UPDATE
# ============================================================


@login_required
@require_POST
def bulk_update_athlete_pathway_requirements(
    request,
    athlete_id,
):
    if not is_head_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only head coaches can '
                'update pathway requirements.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = get_object_or_404(
        AthletePathway,
        athlete=athlete,
    )


    athlete_requirements = (
        AthletePathwayRequirement.objects
        .filter(
            athlete_pathway=(
                athlete_pathway
            ),
            requirement__is_active=True,
        )
        .select_related(
            'requirement',
        )
    )


    allowed_statuses = {
        choice[0]
        for choice
        in (
            AthletePathwayRequirement
            .STATUS_CHOICES
        )
    }


    updated_count = 0


    for athlete_requirement in (
        athlete_requirements
    ):

        requirement_id = (
            athlete_requirement.id
        )


        status = (
            request.POST.get(
                f'status_{requirement_id}',
                athlete_requirement.status,
            )
            .strip()
        )


        coach_note = (
            request.POST.get(
                f'coach_note_{requirement_id}',
                '',
            )
            .strip()
        )


        target_date = (
            request.POST.get(
                f'target_date_{requirement_id}',
                '',
            )
            .strip()
        )


        hidden_from_parent = (
            request.POST.get(
                f'hidden_{requirement_id}'
            )
            == 'yes'
        )


        if status not in allowed_statuses:
            continue


        athlete_requirement.status = (
            status
        )

        athlete_requirement.coach_note = (
            coach_note
        )

        athlete_requirement.target_date = (
            target_date
            or None
        )

        athlete_requirement.is_hidden_from_parent = (
            hidden_from_parent
        )

        athlete_requirement.updated_by = (
            request.user
        )


        athlete_requirement.save(
            update_fields=[
                'status',
                'coach_note',
                'target_date',
                'is_hidden_from_parent',
                'updated_by',
                'updated_at',
            ],
        )


        updated_count += 1


    messages.success(
        request,
        (
            f'{updated_count} pathway '
            'requirements were saved.'
        ),
    )


    return redirect(
        'pathway:athlete_pathway_requirements',
        athlete_id=athlete.id,
    )


# ============================================================
# READ-ONLY PATHWAY OVERVIEW
# ============================================================


@login_required
def pathway_overview(request):
    if not can_view_pathway(request.user):
        messages.error(
            request,
            'You do not have access to the HP Pathway.',
        )

        return redirect('role_redirect')

    levels = (
        PathwayLevel.objects
        .filter(is_active=True)
        .order_by('order')
    )

    level_cards = []

    for level in levels:
        requirements = (
            PathwayRequirement.objects
            .filter(
                level=level,
                is_active=True,
            )
        )

        level_cards.append({
            'level': level,
            'requirement_count': (
                requirements
                .filter(is_required=True)
                .count()
            ),
            'bonus_count': (
                requirements
                .filter(
                    requirement_type=(
                        PathwayRequirement.TYPE_BONUS
                    ),
                )
                .count()
            ),
        })

    parent_pathway_cards = []

    program_sections = [
        {'code': code, 'name': name,
         'cards': [card for card in level_cards if card['level'].program == code]}
        for code, name in PathwayLevel.PROGRAM_CHOICES
        if any(card['level'].program == code for card in level_cards)
    ]

    if request.user.role == 'parent':
        parent_links = (
            get_approved_parent_links(request.user)
            .order_by(
                'athlete__first_name',
                'athlete__last_name',
                'athlete__username',
            )
        )

        for link in parent_links:
            athlete = link.athlete

            athlete_pathway = (
                AthletePathway.objects
                .filter(athlete=athlete)
                .select_related(
                    'current_level',
                    'target_level',
                )
                .first()
            )

            current_progress = None
            target_progress = None

            if athlete_pathway:
                visible_requirements = (
                    AthletePathwayRequirement.objects
                    .filter(
                        athlete_pathway=athlete_pathway,
                        requirement__is_active=True,
                        requirement__is_required=True,
                        is_hidden_from_parent=False,
                    )
                    .select_related(
                        'requirement',
                        'requirement__level',
                    )
                )

                def calculate_level_progress(level):
                    if level is None:
                        return None

                    level_requirements = (
                        visible_requirements
                        .filter(
                            requirement__level=level,
                        )
                    )

                    required_count = (
                        level_requirements.count()
                    )

                    completed_count = (
                        level_requirements
                        .filter(
                            status=(
                                AthletePathwayRequirement
                                .STATUS_COMPETITION_READY
                            ),
                        )
                        .count()
                    )

                    if required_count:
                        percentage = round(
                            (
                                completed_count
                                / required_count
                            )
                            * 100
                        )
                    else:
                        percentage = 0

                    return {
                        'level': level,
                        'required_count': required_count,
                        'completed_count': completed_count,
                        'percentage': percentage,
                    }

                current_progress = (
                    calculate_level_progress(
                        athlete_pathway.current_level
                    )
                )

                if (
                    athlete_pathway.target_level_id
                    == athlete_pathway.current_level_id
                ):
                    target_progress = current_progress
                else:
                    target_progress = (
                        calculate_level_progress(
                            athlete_pathway.target_level
                        )
                    )

            parent_pathway_cards.append({
                'athlete': athlete,
                'pathway': athlete_pathway,
                'current_progress': current_progress,
                'target_progress': target_progress,
            })

    return render(
        request,
        'pathway/pathway_overview.html',
        {
            'level_cards': level_cards,
            'program_sections': program_sections,
            'parent_pathway_cards': (
                parent_pathway_cards
            ),
        },
    )

@login_required
def parent_athlete_pathway(
    request,
    athlete_id,
):
    if request.user.role != 'parent':
        messages.error(
            request,
            'Only parents can access this page.',
        )

        return redirect('role_redirect')

    parent_link = get_object_or_404(
        get_approved_parent_links(request.user),
        athlete_id=athlete_id,
    )

    athlete = parent_link.athlete

    athlete_pathway = get_object_or_404(
        AthletePathway.objects
        .select_related(
            'athlete',
            'current_level',
            'target_level',
        ),
        athlete=athlete,
    )

    selected_levels = []

    if athlete_pathway.current_level_id:
        selected_levels.append({
            'level': athlete_pathway.current_level,
            'label': 'Current Level',
        })

    if athlete_pathway.target_level_id:
        if (
            athlete_pathway.target_level_id
            == athlete_pathway.current_level_id
        ):
            if selected_levels:
                selected_levels[0]['label'] = (
                    'Current & Target Level'
                )
        else:
            selected_levels.append({
                'level': athlete_pathway.target_level,
                'label': 'Target Level',
            })

    selected_level_ids = [
        item['level'].id
        for item in selected_levels
    ]

    athlete_requirements = list(
        AthletePathwayRequirement.objects
        .filter(
            athlete_pathway=athlete_pathway,
            requirement__is_active=True,
            requirement__level_id__in=(
                selected_level_ids
            ),
            is_hidden_from_parent=False,
        )
        .select_related(
            'requirement',
            'requirement__level',
            'requirement__event',
        )
        .order_by(
            'requirement__level__order',
            'requirement__event__order',
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )

    level_progress = []

    for selected_level in selected_levels:
        level = selected_level['level']

        required_items = [
            item
            for item in athlete_requirements
            if (
                item.requirement.level_id == level.id
                and item.requirement.is_required
            )
        ]

        completed_items = [
            item
            for item in required_items
            if (
                item.status
                == AthletePathwayRequirement
                .STATUS_COMPETITION_READY
            )
        ]

        required_count = len(required_items)
        completed_count = len(completed_items)

        if required_count:
            completion_percentage = round(
                (
                    completed_count
                    / required_count
                )
                * 100
            )
        else:
            completion_percentage = 0

        level_progress.append({
            'level': level,
            'label': selected_level['label'],
            'required_count': required_count,
            'completed_count': completed_count,
            'completion_percentage': (
                completion_percentage
            ),
        })

    events = (
        PathwayEvent.objects
        .all()
        .order_by('order')
    )

    event_sections = []

    for event in events:
        event_requirements = [
            item
            for item in athlete_requirements
            if item.requirement.event_id == event.id
        ]

        if not event_requirements:
            continue

        required_items = [
            item
            for item in event_requirements
            if item.requirement.is_required
        ]

        completed_items = [
            item
            for item in required_items
            if (
                item.status
                == AthletePathwayRequirement
                .STATUS_COMPETITION_READY
            )
        ]

        required_count = len(required_items)
        completed_count = len(completed_items)

        if required_count:
            completion_percentage = round(
                (
                    completed_count
                    / required_count
                )
                * 100
            )
        else:
            completion_percentage = 0

        event_sections.append({
            'event': event,
            'requirements': event_requirements,
            'required_count': required_count,
            'completed_count': completed_count,
            'completion_percentage': (
                completion_percentage
            ),
        })

    total_required = sum(
        item['required_count']
        for item in level_progress
    )

    total_completed = sum(
        item['completed_count']
        for item in level_progress
    )

    if total_required:
        overall_percentage = round(
            (
                total_completed
                / total_required
            )
            * 100
        )
    else:
        overall_percentage = 0

    return render(
        request,
        'pathway/parent_athlete_pathway.html',
        {
            'athlete': athlete,
            'athlete_pathway': athlete_pathway,
            'level_progress': level_progress,
            'event_sections': event_sections,
            'total_required': total_required,
            'total_completed': total_completed,
            'overall_percentage': (
                overall_percentage
            ),
        },
    )

# ============================================================
# READ-ONLY LEVEL DETAIL
# ============================================================


@login_required
def pathway_level_detail(
    request,
    level_id,
):
    if not can_view_pathway(
        request.user
    ):

        messages.error(
            request,
            (
                'You do not have access '
                'to the HP Pathway.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    level = get_object_or_404(
        PathwayLevel.objects.filter(
            is_active=True,
        ),
        id=level_id,
    )


    events = (
        PathwayEvent.objects
        .all()
        .order_by(
            'order',
        )
    )


    event_sections = []


    for event in events:

        requirements = (
            PathwayRequirement.objects
            .filter(
                level=level,
                event=event,
                is_active=True,
            )
            .order_by(
                'display_order',
                'requirement_number',
                'title',
            )
        )


        if requirements.exists():

            event_sections.append({
                'event': event,

                'requirements': (
                    requirements
                ),
            })


    previous_level = (
        PathwayLevel.objects
        .filter(
            is_active=True,
            program=level.program,
            order__lt=level.order,
        )
        .order_by(
            '-order',
        )
        .first()
    )


    next_level = (
        PathwayLevel.objects
        .filter(
            is_active=True,
            program=level.program,
            order__gt=level.order,
        )
        .order_by(
            'order',
        )
        .first()
    )


    context = {
        'level': level,
        'progression_levels': PathwayLevel.objects.filter(
            is_active=True, program=level.program,
        ).order_by('order', 'name'),

        'event_sections': (
            event_sections
        ),

        'previous_level': (
            previous_level
        ),

        'next_level': (
            next_level
        ),
    }


    return render(
        request,
        'pathway/pathway_level_detail.html',
        context,
    )


# ============================================================
# BARS D-SCORE CALCULATOR
# ============================================================


@login_required
@hp_scoring_only
def bars_d_score_calculator(
    request,
    athlete_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can use '
                'the D-score calculator.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = (
        AthletePathway.objects
        .filter(
            athlete=athlete,
        )
        .select_related(
            'current_level',
            'target_level',
        )
        .first()
    )


    routine = (
        AthleteRoutine.objects
        .filter(
            athlete=athlete,
            event=(
                AthleteRoutine.EVENT_BARS
            ),
            is_current=True,
        )
        .select_related(
            'pathway_level',
        )
        .first()
    )


    if not routine:

        routine = (
            AthleteRoutine.objects
            .create(
                athlete=athlete,

                event=(
                    AthleteRoutine.EVENT_BARS
                ),

                pathway_level=(
                    athlete_pathway.current_level
                    if athlete_pathway
                    else None
                ),

                name=(
                    'Current Bars Routine'
                ),

                is_current=True,

                created_by=(
                    request.user
                ),
            )
        )


    sync_routine_requirements(
        routine
    )


    if request.method == 'POST':

        action = (
            request.POST.get(
                'action'
            )
        )


        if action == 'add_element':

            form = (
                AthleteRoutineElementForm(
                    request.POST
                )
            )


            if form.is_valid():

                element = (
                    form.save(
                        commit=False
                    )
                )

                element.routine = (
                    routine
                )

                element.save()


                update_element_difficulty_value(
                    element
                )


                messages.success(
                    request,
                    (
                        f'{element.skill_name} '
                        'was added to the routine.'
                    ),
                )


                return redirect(
                    'pathway:bars_d_score_calculator',
                    athlete_id=athlete.id,
                )


        elif action == 'save_requirements':

            routine_requirements = (
                routine
                .routine_requirements
                .all()
            )


            for item in routine_requirements:

                item.is_met = (
                    request.POST.get(
                        f'requirement_{item.id}'
                    )
                    == 'yes'
                )

                item.save(
                    update_fields=[
                        'is_met',
                    ]
                )


            messages.success(
                request,
                (
                    'Bars routine requirements '
                    'were updated.'
                ),
            )


            return redirect(
                'pathway:bars_d_score_calculator',
                athlete_id=athlete.id,
            )


    else:

        form = (
            AthleteRoutineElementForm()
        )


    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    routine_requirements = (
        routine
        .routine_requirements
        .select_related(
            'requirement',
        )
        .order_by(
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )


    athlete_requirement_statuses = {
        item.requirement_id: item
        for item
        in (
            AthletePathwayRequirement.objects
            .filter(
                athlete_pathway__athlete=(
                    athlete
                ),

                requirement__level=(
                    routine.pathway_level
                ),

                requirement__event__code=(
                    'bars'
                ),
            )
            .select_related(
                'requirement',
            )
        )
    }


    requirement_rows = []


    for item in routine_requirements:

        athlete_status = (
            athlete_requirement_statuses
            .get(
                item.requirement_id
            )
        )


        requirement_rows.append({
            'routine_requirement': item,

            'athlete_requirement': (
                athlete_status
            ),
        })


    score = (
        calculate_routine_d_score(
            routine
        )
    )


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'routine': routine,

        'elements': elements,

        'requirement_rows': (
            requirement_rows
        ),

        'element_form': form,

        'element_dv': (
            score[
                'element_dv'
            ]
        ),

        'cr_total': (
            score[
                'cr_total'
            ]
        ),

        'bonus_total': (
            score[
                'bonus_total'
            ]
        ),

        'projected_d_score': (
            score[
                'projected_d_score'
            ]
        ),
    }


    return render(
        request,
        'pathway/bars_d_score_calculator.html',
        context,
    )


# ============================================================
# BEAM D-SCORE CALCULATOR
# ============================================================


@login_required
@hp_scoring_only
def beam_d_score_calculator(
    request,
    athlete_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can use '
                'the D-score calculator.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = (
        AthletePathway.objects
        .filter(
            athlete=athlete,
        )
        .select_related(
            'current_level',
            'target_level',
        )
        .first()
    )


    routine = (
        AthleteRoutine.objects
        .filter(
            athlete=athlete,

            event=(
                AthleteRoutine.EVENT_BEAM
            ),

            is_current=True,
        )
        .select_related(
            'pathway_level',
        )
        .first()
    )


    if not routine:

        routine = (
            AthleteRoutine.objects
            .create(
                athlete=athlete,

                event=(
                    AthleteRoutine.EVENT_BEAM
                ),

                pathway_level=(
                    athlete_pathway.current_level
                    if athlete_pathway
                    else None
                ),

                name=(
                    'Current Beam Routine'
                ),

                is_current=True,

                created_by=(
                    request.user
                ),
            )
        )


    sync_routine_requirements(
        routine
    )


    if request.method == 'POST':

        action = (
            request.POST.get(
                'action'
            )
        )


        if action == 'add_element':

            form = (
                AthleteRoutineElementForm(
                    request.POST
                )
            )


            if form.is_valid():

                element = (
                    form.save(
                        commit=False
                    )
                )

                element.routine = (
                    routine
                )

                element.save()


                update_element_difficulty_value(
                    element
                )


                messages.success(
                    request,
                    (
                        f'{element.skill_name} '
                        'was added to the Beam routine.'
                    ),
                )


                return redirect(
                    'pathway:beam_d_score_calculator',
                    athlete_id=athlete.id,
                )


        elif action == 'save_requirements':

            routine_requirements = (
                routine
                .routine_requirements
                .all()
            )


            for item in routine_requirements:

                item.is_met = (
                    request.POST.get(
                        f'requirement_{item.id}'
                    )
                    == 'yes'
                )

                item.save(
                    update_fields=[
                        'is_met',
                    ]
                )


            messages.success(
                request,
                (
                    'Beam routine requirements '
                    'were updated.'
                ),
            )


            return redirect(
                'pathway:beam_d_score_calculator',
                athlete_id=athlete.id,
            )


    else:

        form = (
            AthleteRoutineElementForm()
        )


    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    routine_requirements = (
        routine
        .routine_requirements
        .select_related(
            'requirement',
        )
        .order_by(
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )


    athlete_requirement_statuses = {
        item.requirement_id: item
        for item
        in (
            AthletePathwayRequirement.objects
            .filter(
                athlete_pathway__athlete=(
                    athlete
                ),

                requirement__level=(
                    routine.pathway_level
                ),

                requirement__event__code=(
                    'beam'
                ),
            )
            .select_related(
                'requirement',
            )
        )
    }


    requirement_rows = []


    for item in routine_requirements:

        athlete_status = (
            athlete_requirement_statuses
            .get(
                item.requirement_id
            )
        )


        requirement_rows.append({
            'routine_requirement': item,

            'athlete_requirement': (
                athlete_status
            ),
        })


    score = (
        calculate_beam_d_score(
            routine
        )
    )


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'routine': routine,

        'elements': elements,

        'requirement_rows': (
            requirement_rows
        ),

        'element_form': form,

        'element_dv': (
            score[
                'element_dv'
            ]
        ),

        'cr_total': (
            score[
                'cr_total'
            ]
        ),

        'bonus_total': (
            score[
                'bonus_total'
            ]
        ),

        'projected_d_score': (
            score[
                'projected_d_score'
            ]
        ),

        'acro_count': (
            score[
                'acro_count'
            ]
        ),

        'dance_count': (
            score[
                'dance_count'
            ]
        ),

        'total_element_count': (
            score[
                'total_element_count'
            ]
        ),

        'acro_requirement_met': (
            score[
                'acro_requirement_met'
            ]
        ),

        'dance_requirement_met': (
            score[
                'dance_requirement_met'
            ]
        ),

        'optional_requirement_met': (
            score[
                'optional_requirement_met'
            ]
        ),
    }


    return render(
        request,
        'pathway/beam_d_score_calculator.html',
        context,
    )


# ============================================================
# DELETE ROUTINE ELEMENT
# ============================================================


@login_required
@require_POST
def delete_routine_element(
    request,
    element_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can edit '
                'routine elements.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    element = get_object_or_404(
        AthleteRoutineElement.objects
        .select_related(
            'routine',
            'routine__athlete',
        ),
        id=element_id,
    )


    athlete_id = (
        element.routine.athlete_id
    )


    event = (
        element.routine.event
    )


    element.delete()


    messages.success(
        request,
        'Routine element removed.',
    )

    if (
            event
            ==
            AthleteRoutine.EVENT_BEAM
    ):
        return redirect(
            'pathway:beam_d_score_calculator',
            athlete_id=athlete_id,
        )

    if (
            event
            ==
            AthleteRoutine.EVENT_FLOOR
    ):
        return redirect(
            'pathway:floor_d_score_calculator',
            athlete_id=athlete_id,
        )

    if (
            event
            ==
            AthleteRoutine.EVENT_VAULT
    ):
        return redirect(
            'pathway:vault_d_score_calculator',
            athlete_id=athlete_id,
        )

    return redirect(
        'pathway:bars_d_score_calculator',
        athlete_id=athlete_id,
    )



@login_required
@hp_scoring_only
def floor_d_score_calculator(
    request,
    athlete_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can use '
                'the D-score calculator.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = (
        AthletePathway.objects
        .filter(
            athlete=athlete,
        )
        .select_related(
            'current_level',
            'target_level',
        )
        .first()
    )


    routine = (
        AthleteRoutine.objects
        .filter(
            athlete=athlete,
            event=(
                AthleteRoutine.EVENT_FLOOR
            ),
            is_current=True,
        )
        .select_related(
            'pathway_level',
        )
        .first()
    )


    if not routine:

        routine = (
            AthleteRoutine.objects
            .create(
                athlete=athlete,

                event=(
                    AthleteRoutine.EVENT_FLOOR
                ),

                pathway_level=(
                    athlete_pathway.current_level
                    if athlete_pathway
                    else None
                ),

                name=(
                    'Current Floor Routine'
                ),

                is_current=True,

                created_by=(
                    request.user
                ),
            )
        )


    sync_routine_requirements(
        routine
    )


    if request.method == 'POST':

        action = (
            request.POST.get(
                'action'
            )
        )


        if action == 'add_element':

            form = (
                AthleteRoutineElementForm(
                    request.POST
                )
            )


            if form.is_valid():

                element = (
                    form.save(
                        commit=False
                    )
                )

                element.routine = (
                    routine
                )

                element.save()


                update_element_difficulty_value(
                    element
                )


                messages.success(
                    request,
                    (
                        f'{element.skill_name} '
                        'was added to the Floor routine.'
                    ),
                )


                return redirect(
                    'pathway:floor_d_score_calculator',
                    athlete_id=athlete.id,
                )


        elif action == 'save_requirements':

            routine_requirements = (
                routine
                .routine_requirements
                .all()
            )


            for item in routine_requirements:

                item.is_met = (
                    request.POST.get(
                        f'requirement_{item.id}'
                    )
                    == 'yes'
                )

                item.save(
                    update_fields=[
                        'is_met',
                    ]
                )


            messages.success(
                request,
                (
                    'Floor routine requirements '
                    'were updated.'
                ),
            )


            return redirect(
                'pathway:floor_d_score_calculator',
                athlete_id=athlete.id,
            )


    else:

        form = (
            AthleteRoutineElementForm()
        )


    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    routine_requirements = (
        routine
        .routine_requirements
        .select_related(
            'requirement',
        )
        .order_by(
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )


    athlete_requirement_statuses = {
        item.requirement_id: item
        for item
        in (
            AthletePathwayRequirement.objects
            .filter(
                athlete_pathway__athlete=(
                    athlete
                ),

                requirement__level=(
                    routine.pathway_level
                ),

                requirement__event__code=(
                    'floor'
                ),
            )
            .select_related(
                'requirement',
            )
        )
    }


    requirement_rows = []


    for item in routine_requirements:

        athlete_status = (
            athlete_requirement_statuses
            .get(
                item.requirement_id
            )
        )


        requirement_rows.append({
            'routine_requirement': item,

            'athlete_requirement': (
                athlete_status
            ),
        })


    score = (
        calculate_floor_d_score(
            routine
        )
    )


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'routine': routine,

        'elements': elements,

        'requirement_rows': (
            requirement_rows
        ),

        'element_form': form,

        'element_dv': (
            score['element_dv']
        ),

        'cr_total': (
            score['cr_total']
        ),

        'bonus_total': (
            score['bonus_total']
        ),

        'projected_d_score': (
            score['projected_d_score']
        ),

        'acro_count': (
            score['acro_count']
        ),

        'dance_count': (
            score['dance_count']
        ),

        'total_element_count': (
            score['total_element_count']
        ),

        'acro_requirement_met': (
            score['acro_requirement_met']
        ),

        'dance_requirement_met': (
            score['dance_requirement_met']
        ),

        'optional_requirement_met': (
            score['optional_requirement_met']
        ),
    }


    return render(
        request,
        'pathway/floor_d_score_calculator.html',
        context,
    )


@login_required
@hp_scoring_only
def vault_d_score_calculator(
    request,
    athlete_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can use '
                'the D-score calculator.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = (
        AthletePathway.objects
        .filter(
            athlete=athlete,
        )
        .select_related(
            'current_level',
            'target_level',
        )
        .first()
    )


    routine = (
        AthleteRoutine.objects
        .filter(
            athlete=athlete,
            event=(
                AthleteRoutine.EVENT_VAULT
            ),
            is_current=True,
        )
        .select_related(
            'pathway_level',
        )
        .first()
    )


    if not routine:

        routine = (
            AthleteRoutine.objects
            .create(
                athlete=athlete,

                event=(
                    AthleteRoutine.EVENT_VAULT
                ),

                pathway_level=(
                    athlete_pathway.current_level
                    if athlete_pathway
                    else None
                ),

                name=(
                    'Current Vault'
                ),

                is_current=True,

                created_by=(
                    request.user
                ),
            )
        )


    sync_routine_requirements(
        routine
    )


    if request.method == 'POST':

        action = (
            request.POST.get(
                'action'
            )
        )


        # ========================================================
        # ADD / REPLACE VAULT
        # ========================================================

        if action == 'add_element':

            form = (
                AthleteRoutineElementForm(
                    request.POST
                )
            )


            if form.is_valid():

                #
                # Vault uses one selected vault,
                # so replace the existing element.
                #
                routine.elements.all().delete()


                element = (
                    form.save(
                        commit=False
                    )
                )

                element.routine = (
                    routine
                )

                element.element_type = (
                    AthleteRoutineElement
                    .ELEMENT_ACRO
                )

                element.order = 1

                element.save()


                update_element_difficulty_value(
                    element
                )


                messages.success(
                    request,
                    (
                        f'{element.skill_name} '
                        'was selected as the vault.'
                    ),
                )


                return redirect(
                    'pathway:vault_d_score_calculator',
                    athlete_id=athlete.id,
                )


        # ========================================================
        # SAVE VAULT BONUSES / REQUIREMENTS
        # ========================================================

        elif action == 'save_requirements':

            routine_requirements = (
                routine
                .routine_requirements
                .all()
            )


            for item in routine_requirements:

                item.is_met = (
                    request.POST.get(
                        f'requirement_{item.id}'
                    )
                    == 'yes'
                )

                item.save(
                    update_fields=[
                        'is_met',
                    ]
                )


            messages.success(
                request,
                (
                    'Vault requirements '
                    'were updated.'
                ),
            )


            return redirect(
                'pathway:vault_d_score_calculator',
                athlete_id=athlete.id,
            )


    else:

        form = (
            AthleteRoutineElementForm()
        )


    elements = (
        routine.elements
        .all()
        .order_by(
            'order',
        )
    )


    routine_requirements = (
        routine
        .routine_requirements
        .select_related(
            'requirement',
        )
        .order_by(
            'requirement__display_order',
            'requirement__requirement_number',
        )
    )


    athlete_requirement_statuses = {
        item.requirement_id: item
        for item
        in (
            AthletePathwayRequirement.objects
            .filter(
                athlete_pathway__athlete=(
                    athlete
                ),

                requirement__level=(
                    routine.pathway_level
                ),

                requirement__event__code=(
                    'vault'
                ),
            )
            .select_related(
                'requirement',
            )
        )
    }


    requirement_rows = []


    for item in routine_requirements:

        athlete_status = (
            athlete_requirement_statuses
            .get(
                item.requirement_id
            )
        )


        requirement_rows.append({
            'routine_requirement': item,

            'athlete_requirement': (
                athlete_status
            ),
        })


    score = (
        calculate_vault_d_score(
            routine
        )
    )


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'routine': routine,

        'elements': elements,

        'requirement_rows': (
            requirement_rows
        ),

        'element_form': form,

        'selected_vault': (
            score[
                'selected_vault'
            ]
        ),

        'vault_dv': (
            score[
                'vault_dv'
            ]
        ),

        'bonus_total': (
            score[
                'bonus_total'
            ]
        ),

        'projected_d_score': (
            score[
                'projected_d_score'
            ]
        ),
    }


    return render(
        request,
        'pathway/vault_d_score_calculator.html',
        context,
    )

@login_required
@hp_scoring_only
def athlete_d_score_dashboard(
    request,
    athlete_id,
):
    if not is_coach(
        request.user
    ):

        messages.error(
            request,
            (
                'Only coaches can view '
                'the D-score dashboard.'
            ),
        )

        return redirect(
            'role_redirect'
        )


    athlete = get_object_or_404(
        User.objects.filter(
            role='athlete',
            is_active=True,
        ),
        id=athlete_id,
    )


    athlete_pathway = (
        AthletePathway.objects
        .filter(
            athlete=athlete,
        )
        .select_related(
            'current_level',
            'target_level',
        )
        .first()
    )


    routines = {
        routine.event: routine
        for routine
        in (
            AthleteRoutine.objects
            .filter(
                athlete=athlete,
                is_current=True,
            )
            .select_related(
                'pathway_level',
            )
        )
    }


    # ========================================================
    # VAULT
    # ========================================================

    vault_routine = routines.get(
        AthleteRoutine.EVENT_VAULT
    )

    if vault_routine:

        vault_score = (
            calculate_vault_d_score(
                vault_routine
            )
        )

    else:

        vault_score = {
            'projected_d_score': 0,
            'vault_dv': 0,
            'bonus_total': 0,
        }


    # ========================================================
    # BARS
    # ========================================================

    bars_routine = routines.get(
        AthleteRoutine.EVENT_BARS
    )

    if bars_routine:

        bars_score = (
            calculate_routine_d_score(
                bars_routine
            )
        )

    else:

        bars_score = {
            'projected_d_score': 0,
            'element_dv': 0,
            'cr_total': 0,
            'bonus_total': 0,
        }


    # ========================================================
    # BEAM
    # ========================================================

    beam_routine = routines.get(
        AthleteRoutine.EVENT_BEAM
    )

    if beam_routine:

        beam_score = (
            calculate_beam_d_score(
                beam_routine
            )
        )

    else:

        beam_score = {
            'projected_d_score': 0,
            'element_dv': 0,
            'cr_total': 0,
            'bonus_total': 0,
        }


    # ========================================================
    # FLOOR
    # ========================================================

    floor_routine = routines.get(
        AthleteRoutine.EVENT_FLOOR
    )

    if floor_routine:

        floor_score = (
            calculate_floor_d_score(
                floor_routine
            )
        )

    else:

        floor_score = {
            'projected_d_score': 0,
            'element_dv': 0,
            'cr_total': 0,
            'bonus_total': 0,
        }


    event_cards = [
        {
            'event': 'Vault',
            'icon': '🏃',
            'routine': vault_routine,
            'score': vault_score[
                'projected_d_score'
            ],
            'url_name': (
                'pathway:vault_d_score_calculator'
            ),
        },
        {
            'event': 'Bars',
            'icon': '🤸',
            'routine': bars_routine,
            'score': bars_score[
                'projected_d_score'
            ],
            'url_name': (
                'pathway:bars_d_score_calculator'
            ),
        },
        {
            'event': 'Beam',
            'icon': '⚖️',
            'routine': beam_routine,
            'score': beam_score[
                'projected_d_score'
            ],
            'url_name': (
                'pathway:beam_d_score_calculator'
            ),
        },
        {
            'event': 'Floor',
            'icon': '🎵',
            'routine': floor_routine,
            'score': floor_score[
                'projected_d_score'
            ],
            'url_name': (
                'pathway:floor_d_score_calculator'
            ),
        },
    ]


    context = {
        'athlete': athlete,

        'athlete_pathway': (
            athlete_pathway
        ),

        'event_cards': (
            event_cards
        ),
    }


    return render(
        request,
        'pathway/athlete_d_score_dashboard.html',
        context,
    )
