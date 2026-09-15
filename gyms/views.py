from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from communications.dashboard import get_dashboard_communication_data

from athletes.models import (
    AthleteProfile,
    AttendanceRecord,
    AthleteSkill,
    AthleteVideo,
)
from coaches.models import CoachNote, CoachProfile, TeamEvent
from parents_portal.models import (
    ParentAthleteLink,
    ParentProfile,
)
from performance_testing.models import AthleteTestingResult
from surveys.models import DailySurvey

from .forms import (
    CreateGymPersonForm,
    EditGymPersonForm,
    LinkParentGuardianForm,
    ManageGroupAthletesForm,
    ManageGroupCoachesForm,
    TrainingGroupForm,
)
from .models import (
    Gym,
    GymMembership,
    TrainingGroup,
    TrainingGroupAthlete,
    TrainingGroupCoach,
)

User = get_user_model()

def get_director_gym(request_user):
    """
    Return the application's gym for a Director.

    The app currently supports one gym, so Directors are
    automatically assigned to the first available gym.
    """

    if request_user.role != "director":
        return None

    gym = Gym.objects.first()

    if not gym:
        return None

    GymMembership.objects.update_or_create(
        user=request_user,
        gym=gym,
        defaults={
            "role": "director",
            "is_active": True,
        },
    )

    return gym
@login_required
def director_dashboard(request):

    gym = get_director_gym(request.user)
    today = timezone.localdate()

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'role': request.user.role,
                'username': request.user.username,
            }
        )

    memberships = (
        GymMembership.objects
        .filter(
            gym=gym,
            is_active=True
        )
        .select_related('user')
    )

    directors = memberships.filter(
        role='director'
    )

    head_coaches = memberships.filter(
        role='head_coach'
    )

    coaches = memberships.filter(
        role='coach'
    )

    athletes = memberships.filter(
        role='athlete'
    )

    parents = memberships.filter(
        role='parent'
    )

    training_groups = (
        TrainingGroup.objects
        .filter(
            gym=gym,
            is_active=True
        )
        .prefetch_related(
            'coach_assignments__coach',
            'athlete_assignments__athlete'
        )
        .order_by('name')
    )

    group_data = []

    for group in training_groups:

        active_athletes = (
            group.athlete_assignments
            .filter(is_active=True)
            .select_related('athlete')
        )

        coach_assignments = (
            group.coach_assignments
            .select_related('coach')
        )

        group_data.append({
            'group': group,
            'athlete_count': active_athletes.count(),
            'athletes': active_athletes,
            'coaches': coach_assignments,
        })

    upcoming_events = (
        TeamEvent.objects
        .filter(
            gym=gym,
            event_date__gte=today
        )
        .select_related('created_by')
        .order_by(
            'event_date',
            'start_time'
        )[:6]
    )

    upcoming_event_count = (
        TeamEvent.objects
        .filter(
            gym=gym,
            event_date__gte=today
        )
        .count()
    )

    context = {
        'gym': gym,

        'directors': directors,
        'head_coaches': head_coaches,
        'coaches': coaches,
        'athletes': athletes,
        'parents': parents,

        'director_count': directors.count(),
        'head_coach_count': head_coaches.count(),
        'coach_count': coaches.count(),
        'athlete_count': athletes.count(),
        'parent_count': parents.count(),
        'dashboard_communication': (
            get_dashboard_communication_data(
                request.user
            )
        ),

        'training_groups': training_groups,
        'group_count': training_groups.count(),

        'group_data': group_data,
        # Events
        'upcoming_events': upcoming_events,
        'upcoming_event_count': upcoming_event_count,
    }

    return render(
        request,
        'gyms/director_dashboard.html',
        context
    )

@login_required
def director_event_list(request):
    """
    Display upcoming and past events for the director's gym.
    """

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    today = timezone.localdate()

    upcoming_events = (
        TeamEvent.objects
        .filter(
            gym=gym,
            event_date__gte=today
        )
        .select_related('created_by')
        .order_by(
            'event_date',
            'start_time'
        )
    )

    past_events = (
        TeamEvent.objects
        .filter(
            gym=gym,
            event_date__lt=today
        )
        .select_related('created_by')
        .order_by(
            '-event_date',
            '-start_time'
        )[:25]
    )

    return render(
        request,
        'gyms/director_event_list.html',
        {
            'gym': gym,
            'today': today,
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'upcoming_event_count': upcoming_events.count(),
        }
    )


@login_required
def edit_gym_event(request, event_id):
    """
    Allow a director to edit an event belonging to their gym.
    """

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    event = get_object_or_404(
        TeamEvent,
        id=event_id,
        gym=gym
    )

    if request.method == 'POST':
        title = request.POST.get(
            'title',
            ''
        ).strip()

        event_date = request.POST.get(
            'event_date',
            ''
        ).strip()

        if not title or not event_date:
            return render(
                request,
                'gyms/event_form.html',
                {
                    'gym': gym,
                    'event': event,
                    'error': (
                        'An event title and date are required.'
                    ),
                }
            )

        event.title = title
        event.event_date = event_date
        event.start_time = (
            request.POST.get('start_time')
            or None
        )
        event.end_time = (
            request.POST.get('end_time')
            or None
        )
        event.location = request.POST.get(
            'location',
            ''
        ).strip()
        event.description = request.POST.get(
            'description',
            ''
        ).strip()

        event.save(
            update_fields=[
                'title',
                'event_date',
                'start_time',
                'end_time',
                'location',
                'description',
            ]
        )

        messages.success(
            request,
            f'{event.title} was updated successfully.'
        )

        return redirect(
            'director_event_list'
        )

    return render(
        request,
        'gyms/event_form.html',
        {
            'gym': gym,
            'event': event,
        }
    )


@login_required
def delete_gym_event(request, event_id):
    """
    Allow a director to delete an event belonging to their gym.
    """

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    event = get_object_or_404(
        TeamEvent,
        id=event_id,
        gym=gym
    )

    if request.method == 'POST':
        event_title = event.title
        event.delete()

        messages.success(
            request,
            f'{event_title} was deleted.'
        )

        return redirect(
            'director_event_list'
        )

    return render(
        request,
        'gyms/event_confirm_delete.html',
        {
            'gym': gym,
            'event': event,
        }
    )

@login_required
def group_control_panel(request, group_id):
    """
    Director-level control panel for a training group.

    Security:
    The director must belong to the same gym as the group.
    """

    director_membership = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='director',
            is_active=True
        )
        .select_related('gym')
        .first()
    )

    if not director_membership:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    gym = director_membership.gym

    group = get_object_or_404(
        TrainingGroup,
        id=group_id,
        gym=gym,
        is_active=True
    )
    today = timezone.localdate()



    # ---------------------------------------------------------
    # Coaching staff
    # ---------------------------------------------------------

    coach_assignments = (
        group.coach_assignments
        .select_related('coach')
        .order_by(
            'role',
            'coach__first_name',
            'coach__last_name'
        )
    )

    head_coaches = coach_assignments.filter(
        role='head_coach'
    )

    coaches = coach_assignments.exclude(
        role='head_coach'
    )

    # ---------------------------------------------------------
    # Athletes
    # ---------------------------------------------------------

    athlete_assignments = (
        TrainingGroupAthlete.objects
        .filter(
            group=group,
            is_active=True
        )
        .select_related(
            'athlete',
            'athlete__athlete_profile'
        )
        .order_by(
            'athlete__first_name',
            'athlete__last_name',
            'athlete__username'
        )
    )

    athlete_data = []

    for assignment in athlete_assignments:

        athlete = assignment.athlete

        try:
            profile = athlete.athlete_profile
        except AthleteProfile.DoesNotExist:
            profile = None

        # -----------------------------------------------------
        # Parents / Guardians
        # -----------------------------------------------------

        parent_links = (
            ParentAthleteLink.objects
            .filter(
                athlete=athlete,
                approved=True
            )
            .select_related(
                'parent'
            )
            .order_by(
                'parent__first_name',
                'parent__last_name'
            )
        )

        family = []

        for link in parent_links:

            parent = link.parent

            try:
                parent_profile = parent.parent_profile
            except Exception:
                parent_profile = None

            family.append({
                'user': parent,
                'relationship': link.relationship,
                'phone': (
                    parent_profile.phone
                    if parent_profile
                    else ''
                ),
                'email': parent.email,
            })

        # -----------------------------------------------------
        # Attendance
        # -----------------------------------------------------

        latest_attendance = (
            AttendanceRecord.objects
            .filter(
                athlete=athlete
            )
            .order_by(
                '-attendance_date'
            )
            .first()
        )

        today_attendance = (
            AttendanceRecord.objects
            .filter(
                athlete=athlete,
                attendance_date=today
            )
            .first()
        )

        # -----------------------------------------------------
        # Wellness
        # -----------------------------------------------------

        today_survey = (
            DailySurvey.objects
            .filter(
                athlete=athlete,
                survey_date=today
            )
            .first()
        )

        wellness_status = 'not_submitted'
        wellness_label = 'Not Submitted'

        if today_survey:

            needs_attention = (
                today_survey.energy <= 2
                or today_survey.soreness >= 4
                or today_survey.stress >= 4
            )

            if needs_attention:
                wellness_status = 'attention'
                wellness_label = 'Needs Attention'

            else:
                wellness_status = 'ready'
                wellness_label = 'Ready'

        athlete_data.append({
            'assignment': assignment,
            'athlete': athlete,
            'profile': profile,
            'family': family,

            'today_attendance': today_attendance,
            'latest_attendance': latest_attendance,

            'survey': today_survey,
            'wellness_status': wellness_status,
            'wellness_label': wellness_label,
        })

    context = {
        'gym': group.gym,
        'group': group,

        'head_coaches': head_coaches,
        'coaches': coaches,

        'athlete_data': athlete_data,
        'athlete_count': len(athlete_data),

        'today': today,
    }

    return render(
        request,
        'gyms/group_control_panel.html',
        context
    )


@login_required
def create_training_group(request):

    director_membership = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='director',
            is_active=True
        )
        .select_related('gym')
        .first()
    )

    if not director_membership:

        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    gym = director_membership.gym

    if request.method == 'POST':

        form = TrainingGroupForm(request.POST)

        if form.is_valid():

            group = form.save(commit=False)

            # IMPORTANT:
            # The gym comes from the authenticated director.
            # We never allow the browser to choose the gym.
            group.gym = gym

            group.save()

            messages.success(
                request,
                f'{group.name} was created successfully.'
            )

            return redirect(
                'group_control_panel',
                group_id=group.id
            )

    else:

        form = TrainingGroupForm()

    context = {
        'form': form,
        'gym': gym,
        'page_title': 'Create Training Group',
        'submit_text': 'Create Group',
        'is_editing': False,
    }

    return render(
        request,
        'gyms/training_group_form.html',
        context
    )


@login_required
def edit_training_group(request, group_id):

    director_membership = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='director',
            is_active=True
        )
        .select_related('gym')
        .first()
    )

    if not director_membership:

        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    gym = director_membership.gym

    # Cross-gym security:
    # the director can ONLY retrieve groups in their own gym.
    group = get_object_or_404(
        TrainingGroup,
        id=group_id,
        gym=gym,
        is_active=True
    )

    if request.method == 'POST':

        form = TrainingGroupForm(
            request.POST,
            instance=group
        )

        if form.is_valid():

            group = form.save()

            messages.success(
                request,
                f'{group.name} was updated successfully.'
            )

            return redirect(
                'group_control_panel',
                group_id=group.id
            )

    else:

        form = TrainingGroupForm(
            instance=group
        )

    context = {
        'form': form,
        'gym': gym,
        'group': group,
        'page_title': 'Edit Training Group',
        'submit_text': 'Save Changes',
        'is_editing': True,
    }

    return render(
        request,
        'gyms/training_group_form.html',
        context
    )


@login_required
def manage_group_coaches(request, group_id):

    director_membership = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='director',
            is_active=True
        )
        .select_related('gym')
        .first()
    )

    if not director_membership:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    gym = director_membership.gym

    group = get_object_or_404(
        TrainingGroup,
        id=group_id,
        gym=gym,
        is_active=True
    )

    if request.method == 'POST':

        form = ManageGroupCoachesForm(
            request.POST,
            gym=gym,
            group=group
        )

        if form.is_valid():

            head_coach = form.cleaned_data['head_coach']
            selected_coaches = form.cleaned_data['coaches']

            with transaction.atomic():

                # Remove current assignments.
                TrainingGroupCoach.objects.filter(
                    group=group
                ).delete()

                # Add selected head coach.
                if head_coach:

                    TrainingGroupCoach.objects.create(
                        group=group,
                        coach=head_coach,
                        role='head_coach'
                    )

                # Add coaching staff.
                for coach in selected_coaches:

                    # Prevent duplicate assignment if the
                    # head coach was also checked as a coach.
                    if head_coach and coach.id == head_coach.id:
                        continue

                    TrainingGroupCoach.objects.create(
                        group=group,
                        coach=coach,
                        role='coach'
                    )

            messages.success(
                request,
                f'Coaching staff for {group.name} was updated.'
            )

            return redirect(
                'group_control_panel',
                group_id=group.id
            )

    else:

        form = ManageGroupCoachesForm(
            gym=gym,
            group=group
        )

    return render(
        request,
        'gyms/manage_group_coaches.html',
        {
            'gym': gym,
            'group': group,
            'form': form,
        }
    )


@login_required
def manage_group_athletes(request, group_id):

    director_membership = (
        GymMembership.objects
        .filter(
            user=request.user,
            role='director',
            is_active=True
        )
        .select_related('gym')
        .first()
    )

    if not director_membership:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    gym = director_membership.gym

    group = get_object_or_404(
        TrainingGroup,
        id=group_id,
        gym=gym,
        is_active=True
    )

    if request.method == 'POST':

        form = ManageGroupAthletesForm(
            request.POST,
            gym=gym,
            group=group
        )

        if form.is_valid():

            selected_athletes = form.cleaned_data['athletes']

            selected_ids = set(
                selected_athletes.values_list(
                    'id',
                    flat=True
                )
            )

            with transaction.atomic():

                existing_assignments = (
                    TrainingGroupAthlete.objects
                    .filter(group=group)
                )

                # Deactivate athletes that were unchecked.
                existing_assignments.exclude(
                    athlete_id__in=selected_ids
                ).update(
                    is_active=False
                )

                # Add/reactivate selected athletes.
                for athlete in selected_athletes:

                    assignment, created = (
                        TrainingGroupAthlete.objects
                        .get_or_create(
                            group=group,
                            athlete=athlete,
                            defaults={
                                'is_active': True
                            }
                        )
                    )

                    if not created and not assignment.is_active:
                        assignment.is_active = True
                        assignment.save()

            messages.success(
                request,
                f'Athlete roster for {group.name} was updated.'
            )

            return redirect(
                'group_control_panel',
                group_id=group.id
            )

    else:

        form = ManageGroupAthletesForm(
            gym=gym,
            group=group
        )

    return render(
        request,
        'gyms/manage_group_athletes.html',
        {
            'gym': gym,
            'group': group,
            'form': form,
        }
    )


@login_required
def people_management(request):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    memberships = (
        GymMembership.objects
        .filter(gym=gym)
        .select_related('user')
        .order_by(
            'role',
            'user__first_name',
            'user__last_name',
            'user__username'
        )
    )

    head_coaches = memberships.filter(role='head_coach')
    coaches = memberships.filter(role='coach')
    athletes = memberships.filter(role='athlete')
    parents = memberships.filter(role='parent')

    context = {
        'gym': gym,
        'head_coaches': head_coaches,
        'coaches': coaches,
        'athletes': athletes,
        'parents': parents,
        'head_coach_count': head_coaches.filter(is_active=True).count(),
        'coach_count': coaches.filter(is_active=True).count(),
        'athlete_count': athletes.filter(is_active=True).count(),
        'parent_count': parents.filter(is_active=True).count(),
    }

    return render(
        request,
        'gyms/people_management.html',
        context
    )


@login_required
def create_gym_person(request):
    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    if request.method == 'POST':
        form = CreateGymPersonForm(request.POST)

        if form.is_valid():
            username = (
                form.cleaned_data['username']
                .strip()
            )

            username_exists = User.objects.filter(
                username__iexact=username
            ).exists()

            if username_exists:
                form.add_error(
                    'username',
                    (
                        f'The username "{username}" already exists. '
                        'Please choose a different username.'
                    )
                )

            else:
                role = form.cleaned_data['role']

                with transaction.atomic():
                    user = User(
                        username=username,
                        first_name=form.cleaned_data[
                            'first_name'
                        ],
                        last_name=form.cleaned_data[
                            'last_name'
                        ],
                        email=form.cleaned_data[
                            'email'
                        ],
                        role=role,
                    )

                    user.set_password(
                        form.cleaned_data['password']
                    )

                    user.save()

                    GymMembership.objects.create(
                        gym=gym,
                        user=user,
                        role=role,
                        is_active=True
                    )

                    # Athlete profile
                    if role == 'athlete':
                        AthleteProfile.objects.create(
                            user=user,
                            date_of_birth=form.cleaned_data[
                                'date_of_birth'
                            ],
                            level=form.cleaned_data[
                                'level'
                            ],
                            emergency_contact_name=(
                                form.cleaned_data[
                                    'emergency_contact_name'
                                ]
                            ),
                            emergency_contact_phone=(
                                form.cleaned_data[
                                    'emergency_contact_phone'
                                ]
                            ),
                            emergency_contact_relationship=(
                                form.cleaned_data[
                                    'emergency_contact_relationship'
                                ]
                            ),
                            medical_notes=form.cleaned_data[
                                'medical_notes'
                            ],
                        )

                    # Coach profile
                    elif role in [
                        'coach',
                        'head_coach',
                    ]:
                        CoachProfile.objects.create(
                            user=user,
                            title=form.cleaned_data[
                                'title'
                            ],
                            phone=form.cleaned_data[
                                'phone'
                            ],
                        )

                    # Parent profile
                    elif role == 'parent':
                        ParentProfile.objects.create(
                            user=user,
                            phone=form.cleaned_data[
                                'phone'
                            ],
                        )

                messages.success(
                    request,
                    (
                        f'{user.get_full_name() or user.username} '
                        f'was added to {gym.name}.'
                    )
                )

                return redirect(
                    'people_management'
                )

    else:
        form = CreateGymPersonForm()

    return render(
        request,
        'gyms/person_form.html',
        {
            'gym': gym,
            'form': form,
            'page_title': 'Add Person',
            'is_editing': False,
        }
    )

@login_required
def edit_gym_person(request, membership_id):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    membership = get_object_or_404(
        GymMembership.objects.select_related('user'),
        id=membership_id,
        gym=gym,
        role__in=[
            'head_coach',
            'coach',
            'athlete',
            'parent',
        ]
    )

    user = membership.user
    role = membership.role

    profile = None

    if role == 'athlete':
        profile, _ = AthleteProfile.objects.get_or_create(
            user=user
        )

    elif role in ['coach', 'head_coach']:
        profile, _ = CoachProfile.objects.get_or_create(
            user=user
        )

    elif role == 'parent':
        profile, _ = ParentProfile.objects.get_or_create(
            user=user
        )

    if request.method == 'POST':

        form = EditGymPersonForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()

                if role == 'athlete':

                    profile.date_of_birth = (
                        form.cleaned_data['date_of_birth']
                    )

                    profile.level = (
                        form.cleaned_data['level']
                    )

                    profile.emergency_contact_name = (
                        form.cleaned_data['emergency_contact_name']
                    )

                    profile.emergency_contact_phone = (
                        form.cleaned_data['emergency_contact_phone']
                    )

                    profile.emergency_contact_relationship = (
                        form.cleaned_data[
                            'emergency_contact_relationship'
                        ]
                    )

                    profile.medical_notes = (
                        form.cleaned_data['medical_notes']
                    )

                    profile.save()

                elif role in ['coach', 'head_coach']:

                    profile.title = form.cleaned_data['title']
                    profile.phone = form.cleaned_data['phone']
                    profile.save()

                elif role == 'parent':

                    profile.phone = form.cleaned_data['phone']
                    profile.save()

            messages.success(
                request,
                'Profile updated successfully.'
            )

            return redirect('people_management')

    else:

        initial = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        }

        if role == 'athlete':

            initial.update({
                'date_of_birth': profile.date_of_birth,
                'level': profile.level,
                'emergency_contact_name': (
                    profile.emergency_contact_name
                ),
                'emergency_contact_phone': (
                    profile.emergency_contact_phone
                ),
                'emergency_contact_relationship': (
                    profile.emergency_contact_relationship
                ),
                'medical_notes': profile.medical_notes,
            })

        elif role in ['coach', 'head_coach']:

            initial.update({
                'title': profile.title,
                'phone': profile.phone,
            })

        elif role == 'parent':

            initial.update({
                'phone': profile.phone,
            })

        form = EditGymPersonForm(
            initial=initial
        )

    return render(
        request,
        'gyms/person_form.html',
        {
            'gym': gym,
            'form': form,
            'membership': membership,
            'person': user,
            'person_role': role,
            'page_title': 'Edit Person',
            'is_editing': True,
        }
    )


@login_required
def toggle_gym_person_status(request, membership_id):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    membership = get_object_or_404(
        GymMembership.objects.select_related('user'),
        id=membership_id,
        gym=gym,
        role__in=[
            'head_coach',
            'coach',
            'athlete',
            'parent',
        ]
    )

    if request.method == 'POST':

        membership.is_active = not membership.is_active
        membership.save(update_fields=['is_active'])

        status = (
            'activated'
            if membership.is_active
            else 'deactivated'
        )

        messages.success(
            request,
            f'{membership.user.get_full_name() or membership.user.username} '
            f'was {status}.'
        )

    return redirect('people_management')


@login_required
def link_parent_guardian(request, athlete_id):
    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    athlete_membership = get_object_or_404(
        GymMembership.objects.select_related('user'),
        gym=gym,
        user_id=athlete_id,
        role='athlete',
        is_active=True,
    )

    athlete = athlete_membership.user

    if request.method == 'POST':
        form = LinkParentGuardianForm(
            request.POST,
            gym=gym,
        )

        if form.is_valid():
            parent_membership = form.cleaned_data['parent']
            relationship = form.cleaned_data['relationship'].strip()

            parent = parent_membership.user

            existing_link = (
                ParentAthleteLink.objects
                .filter(
                    parent=parent,
                    athlete=athlete,
                )
                .first()
            )

            if existing_link:
                if existing_link.approved:
                    messages.info(
                        request,
                        f'{parent.get_full_name() or parent.username} is already connected to this athlete.'
                    )

                else:
                    existing_link.approved = True
                    existing_link.relationship = relationship
                    existing_link.save(
                        update_fields=[
                            'approved',
                            'relationship',
                        ]
                    )

                    messages.success(
                        request,
                        f'{parent.get_full_name() or parent.username} has been approved and connected to this athlete.'
                    )

                return redirect(
                    'director_athlete_profile',
                    athlete_id=athlete.id,
                )

            ParentAthleteLink.objects.create(
                parent=parent,
                athlete=athlete,
                relationship=relationship,
                approved=True,
            )

            messages.success(
                request,
                f'{parent.get_full_name() or parent.username} has been connected to {athlete.get_full_name() or athlete.username}.'
            )

            return redirect(
                'director_athlete_profile',
                athlete_id=athlete.id,
            )

    else:
        form = LinkParentGuardianForm(
            gym=gym,
        )

    return render(
        request,
        'gyms/link_parent_guardian.html',
        {
            'gym': gym,
            'athlete': athlete,
            'form': form,
        }
    )

@login_required
def director_athlete_profile(request, athlete_id):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    # --------------------------------------------------
    # CRITICAL TENANT CHECK
    # Athlete MUST belong to this director's gym.
    # --------------------------------------------------

    membership = get_object_or_404(
        GymMembership.objects.select_related('user'),
        gym=gym,
        user_id=athlete_id,
        role='athlete',
        is_active=True,
    )

    athlete = membership.user


    # --------------------------------------------------
    # ATHLETE PROFILE
    # --------------------------------------------------

    try:
        profile = athlete.athlete_profile
    except AthleteProfile.DoesNotExist:
        profile = None


    # --------------------------------------------------
    # TRAINING GROUPS
    # --------------------------------------------------

    group_assignments = (
        TrainingGroupAthlete.objects
        .filter(
            athlete=athlete,
            group__gym=gym,
            is_active=True,
            group__is_active=True,
        )
        .select_related('group')
        .order_by('group__name')
    )


    # --------------------------------------------------
    # FAMILY
    # --------------------------------------------------

    approved_parent_links = (
        ParentAthleteLink.objects
        .filter(
            athlete=athlete,
            approved=True,
        )
        .select_related(
            'parent',
            'parent__parent_profile',
        )
        .order_by(
            'parent__first_name',
            'parent__last_name',
        )
    )

    pending_parent_links = (
        ParentAthleteLink.objects
        .filter(
            athlete=athlete,
            approved=False,
        )
        .select_related(
            'parent',
            'parent__parent_profile',
        )
        .order_by(
            'parent__first_name',
            'parent__last_name',
        )
    )

    family = []

    for link in approved_parent_links:

        parent_membership = (
            GymMembership.objects
            .filter(
                gym=gym,
                user=link.parent,
                role='parent',
                is_active=True,
            )
            .first()
        )

        if not parent_membership:
            continue

        try:
            parent_profile = link.parent.parent_profile
        except Exception:
            parent_profile = None

        family.append({
            'link': link,
            'parent': link.parent,
            'relationship': link.relationship,
            'phone': (
                parent_profile.phone
                if parent_profile
                else ''
            ),
        })

    pending_family = []

    for link in pending_parent_links:

        parent_membership = (
            GymMembership.objects
            .filter(
                gym=gym,
                user=link.parent,
                role='parent',
                is_active=True,
            )
            .first()
        )

        if not parent_membership:
            continue

        try:
            parent_profile = link.parent.parent_profile
        except Exception:
            parent_profile = None

        pending_family.append({
            'link': link,
            'parent': link.parent,
            'relationship': link.relationship,
            'phone': (
                parent_profile.phone
                if parent_profile
                else ''
            ),
        })


    # --------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------

    attendance_records = (
        AttendanceRecord.objects
        .filter(athlete=athlete)
        .select_related('coach')
        .order_by('-attendance_date')[:30]
    )

    total_attendance = AttendanceRecord.objects.filter(
        athlete=athlete
    ).count()

    present_count = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='present',
    ).count()

    absent_count = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='absent',
    ).count()

    late_count = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='late',
    ).count()

    if total_attendance:

        attendance_rate = round(
            (
                (
                    present_count
                    + late_count
                )
                / total_attendance
            )
            * 100,
            1,
        )

    else:
        attendance_rate = None


    # --------------------------------------------------
    # WELLNESS
    # --------------------------------------------------

    wellness_surveys = (
        DailySurvey.objects
        .filter(athlete=athlete)
        .order_by('-survey_date')[:14]
    )

    latest_survey = wellness_surveys.first()

    wellness_status = 'not_submitted'
    wellness_label = 'No Recent Survey'

    if latest_survey:

        needs_attention = (
            latest_survey.energy <= 2
            or latest_survey.soreness >= 4
            or latest_survey.stress >= 4
        )

        if needs_attention:

            wellness_status = 'attention'
            wellness_label = 'Needs Attention'

        else:

            wellness_status = 'ready'
            wellness_label = 'Ready'


    # --------------------------------------------------
    # SKILLS
    # --------------------------------------------------

    athlete_skills = (
        AthleteSkill.objects
        .filter(athlete=athlete)
        .select_related(
            'skill',
            'coach',
        )
        .order_by(
            'skill__event',
            'skill__name',
        )
    )

    skill_count = athlete_skills.count()

    mastered_count = athlete_skills.filter(
        status__in=[
            'mastered',
            'competition_ready',
        ]
    ).count()


    # --------------------------------------------------
    # VIDEOS
    # --------------------------------------------------

    videos = (
        AthleteVideo.objects
        .filter(athlete=athlete)
        .select_related(
            'skill',
            'uploaded_by',
        )
        .order_by(
            '-practice_date',
            '-uploaded_at',
        )[:12]
    )


    # --------------------------------------------------
    # COACH NOTES
    # --------------------------------------------------

    coach_notes = (
        CoachNote.objects
        .filter(athlete=athlete)
        .select_related('coach')
        .order_by('-created_at')[:10]
    )


    # --------------------------------------------------
    # PERFORMANCE TESTING
    # --------------------------------------------------

    testing_results = (
        AthleteTestingResult.objects
        .filter(
            athlete=athlete,
            status='verified',
        )
        .select_related('session')
        .prefetch_related(
            'exercise_results__exercise'
        )
        .order_by(
            '-session__testing_date'
        )[:10]
    )


    context = {

        'gym': gym,

        'membership': membership,

        'athlete': athlete,

        'profile': profile,

        'group_assignments': group_assignments,

        'family': family,
        'pending_family': pending_family,

        'attendance_records': attendance_records,

        'attendance_rate': attendance_rate,
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,

        'wellness_surveys': wellness_surveys,
        'latest_survey': latest_survey,
        'wellness_status': wellness_status,
        'wellness_label': wellness_label,

        'athlete_skills': athlete_skills,
        'skill_count': skill_count,
        'mastered_count': mastered_count,

        'videos': videos,

        'coach_notes': coach_notes,

        'testing_results': testing_results,
    }

    return render(
        request,
        'gyms/athlete_profile.html',
        context,
    )


@login_required
def approve_parent_link(request, link_id):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    link = get_object_or_404(
        ParentAthleteLink.objects.select_related(
            'parent',
            'athlete',
        ),
        id=link_id,
    )

    athlete_membership_exists = GymMembership.objects.filter(
        gym=gym,
        user=link.athlete,
        role='athlete',
        is_active=True,
    ).exists()

    parent_membership_exists = GymMembership.objects.filter(
        gym=gym,
        user=link.parent,
        role='parent',
        is_active=True,
    ).exists()

    if not athlete_membership_exists or not parent_membership_exists:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    if request.method == 'POST':

        link.approved = True
        link.save(update_fields=['approved'])

        messages.success(
            request,
            (
                f'{link.parent.get_full_name() or link.parent.username} '
                f'is now connected to '
                f'{link.athlete.get_full_name() or link.athlete.username}.'
            )
        )

    return redirect(
        'director_athlete_profile',
        athlete_id=link.athlete.id,
    )


@login_required
def decline_parent_link(request, link_id):

    gym = get_director_gym(request.user)

    if not gym:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    link = get_object_or_404(
        ParentAthleteLink.objects.select_related(
            'parent',
            'athlete',
        ),
        id=link_id,
    )

    athlete_membership_exists = GymMembership.objects.filter(
        gym=gym,
        user=link.athlete,
        role='athlete',
        is_active=True,
    ).exists()

    parent_membership_exists = GymMembership.objects.filter(
        gym=gym,
        user=link.parent,
        role='parent',
        is_active=True,
    ).exists()

    if not athlete_membership_exists or not parent_membership_exists:
        return render(
            request,
            'coaches/not_allowed.html',
            {
                'username': request.user.username,
                'role': request.user.role,
            }
        )

    athlete_id = link.athlete.id
    parent_name = (
        link.parent.get_full_name()
        or link.parent.username
    )

    if request.method == 'POST':

        link.delete()

        messages.success(
            request,
            f'{parent_name} connection request was declined.'
        )

    return redirect(
        'director_athlete_profile',
        athlete_id=athlete_id,
    )