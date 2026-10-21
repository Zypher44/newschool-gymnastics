from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from gyms.models import GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from parents_portal.models import ParentAthleteLink
from practice_focus.models import AthletePracticePlan
from .access import ROLES, member_gym, practice_scope
from .models import OnboardingProgress


def route(*names):
    for name in names:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return ''


def dashboard(user):
    names = {'director': ('director_dashboard',), 'coach': ('coach_dashboard',),
        'head_coach': ('coach_dashboard',), 'athlete': ('athlete_dashboard',),
        'parent': ('parent_dashboard', 'parents_portal:parent_dashboard')}
    return route(*names.get(user.role, ('role_redirect',))) or '/'


def lesson(key, title, description, points, links=(), status='', demo=False, new=False, note=None):
    return {'key': key, 'title': title, 'description': description, 'points': points,
        'links': [{'label': label, 'url': route(*names)} for label, names in links],
        'status': status, 'demo': demo, 'new': new, 'note': note}


def lessons(user, gym):
    role = user.role
    if role == 'director':
        members = GymMembership.objects.filter(gym=gym, is_active=True, user__is_active=True)
        groups = TrainingGroup.objects.filter(gym=gym, is_active=True)
        linked_groups = groups.filter(coach_assignments__coach__gym_memberships__gym=gym,
            coach_assignments__coach__gym_memberships__is_active=True,
            coach_assignments__coach__is_active=True, coach_assignments__coach__role__in=['coach', 'head_coach'],
            athlete_assignments__is_active=True, athlete_assignments__athlete__is_active=True,
            athlete_assignments__athlete__gym_memberships__gym=gym,
            athlete_assignments__athlete__gym_memberships__is_active=True,
            athlete_assignments__athlete__gym_memberships__role='athlete').distinct().count()
        return [
            lesson('gym', 'Make this your gym', 'Confirm the gym information already on your account.',
                ['Check your gym name, location, and contact information.',
                 'Existing records are reused; this guide does not create another gym.'],
                [('Open gym settings', ('gym_settings',))], gym.name),
            lesson('people', 'Bring your people together', 'Give each person the right role and access.',
                ['Import an Excel or Google Sheets roster, or add people individually through People Management.',
                 'Preview roles, family links and group assignments before confirming an import.',
                 'Approve membership and parent-link requests after checking them.'],
                [('Import / Export People', ('roster_import',)), ('Manage people', ('people_management',))],
                f'{members.count()} active people in this gym'),
            lesson('groups', 'Organize training groups', 'Mixed levels can train together with different individual plans.',
                ['Create a training group, then assign its coaches and athletes.',
                 'A group organizes practice; each child still keeps their own skills and targets.'],
                [('Create a group', ('create_training_group',)), ('Manage existing groups', ('director_dashboard',))],
                f'{groups.count()} active groups · {linked_groups} with a coach and athletes'),
            lesson('practice', 'Prepare your coaching team', 'Coaches build reusable plans and run Start Practice.',
                ['Ask each coach to check their assigned group and personalize the first practice.',
                 'Their Start Practice screen links attendance, individual plans, and both trackers.',
                 'Directors continue managing people and groups from their own dashboard.'],
                [('Open director dashboard', ('director_dashboard',))]),
            lesson('ready', 'Know what families will see', 'Keep parent communication clear and intentional.',
                ['Parents request a child connection; the gym approves access.',
                 'Coaches review athlete entries and publish weekly summaries.',
                 'Private notes stay with coaches. Email delivery uses the separate provider setup.'],
                [('Review your dashboard', ('director_dashboard',))]),
        ]
    if role in ('coach', 'head_coach'):
        gym_id, roster, groups = practice_scope(user)
        plan_count = AthletePracticePlan.objects.filter(gym_id=gym_id, athlete__in=roster,
            practice_date=timezone.localdate()).count()
        return [
            lesson('group', 'Find your training group', 'Start with the athletes you coach.',
                ['Check the group and athlete names before practice.',
                 'If a group is missing, ask your director to check its coach assignments.'],
                [('Open Start Practice', ('practice_hub:start',)), ('Coach dashboard', ('coach_dashboard',))],
                f'{groups.count()} available groups · {roster.count()} athletes'),
            lesson('plan', 'Prepare each child’s plan', 'Use a template, then adjust skills and targets for the individual athlete.',
                ['Choose the athlete and today’s date in Practice Planner.',
                 'Choose event skills and planned skill attempts, routine targets, and pressure sets for that child.',
                 'Save template keeps a reusable structure. Customize the copied plan for each athlete and date.',
                 'Save plan keeps the daily plan separate. Save and set current skills activates today’s skills in the trackers.',
                 'Children in the same group can have different levels and targets. Their own planned attempts appear in Skill Tracker.'],
                [('Open Practice Planner', ('practice_focus:planner',)), ('Manage skills', ('skill_tracker:manage',))],
                f'{plan_count} individual plans saved for today'),
            lesson('track', 'Run a practice quickly', 'Learn the recording buttons without adding real scores.',
                ['Choose the training group in Start Practice, then tap an athlete’s name and event.',
                 'Use the quick attendance action when everyone is present; correct individual attendance in Practice tools.',
                 'Use Start and Stop on the group timer; +1 min and +5 min extend the group’s remaining time.',
                 'Each child has a separate timer. Their event selection stays linked to what they are working on without changing another child’s timer.',
                 'Open Skill Tracker or Routine Tracker for the selected athlete and event. Entries autosave; use Undo for an accidental tap.',
                 'Wow and Hit are successful completions. Attempt records an attempt that did not hit.'],
                [('Open Start Practice', ('practice_hub:start',))], demo=True),
            lesson('review', 'Review before sharing', 'Turn practice entries into useful feedback.',
                ['Review athlete-entered results in the Coach Review Queue.',
                 'Write private notes separately from feedback you choose to share.',
                 'Check the athlete, event, and result before approving an entry for family reports.'],
                [('Coach Review Queue', ('practice_focus:review_queue',)),
                 ('Notes and feedback', ('practice_focus:coach_feedback',))]),
            lesson('reports', 'Share useful progress reports', 'Give families a clear picture of skills, routines, and the next focus.',
                ['Use the Reports Center for athlete progress, skill and routine progress, attendance, testing, and weekly reports.',
                 'Preview the athlete’s approved skill and routine results before publishing their weekly summary.',
                 'In Account Settings, turn off group averages when you want reports to show individual results without group Wow, Hit, and Attempt comparisons.',
                 'Print or prepare report emails from the report page. Email delivery requires the gym’s email provider to be configured.'],
                [('Reports Center', ('report_center',)), ('Weekly Reports', ('practice_focus:weekly_reports',)),
                 ('Account Settings', ('account_settings',))], new=True),
            lesson('passport', 'Make progress worth celebrating', 'Use Practice Passport badges to recognize each athlete’s own journey.',
                ['Open Reports Center → Practice Passport, choose the athlete, and select a badge to award.',
                 'Tell the athlete what the badge recognizes and agree on one small, age-appropriate goal for practice.',
                 'Recognize effort, applying corrections, teamwork, and personal improvement alongside successful skills.',
                 'Use the attendance badge, Practice Pal, to recognize recorded Present and Late practices. Planned breaks do not reset attendance progress.',
                 'Review measurable badge requirements against approved results and attendance; use your observation for learning and teamwork badges.',
                 'Award messages are shared with the athlete and approved linked parents. Explain the specific effort or progress you noticed.',
                 'Create, edit, or delete your gym’s badge options in the badge editor. Previously earned stamps keep their saved details.',
                 'Ask athletes which goals and celebrations motivate them. Keep recognition personal, encouraging, and enjoyable.'],
                [('Practice Passport', ('practice_focus:coach_passport',)),
                 ('Create & edit badges', ('practice_focus:badge_editor',))], new=True,
                note={'title': 'Why gamify practice?',
                      'body': 'Repeated practice can feel more meaningful when children can see small steps forward. Badges give coaches a way to make effort visible, set achievable goals, and celebrate the learning that happens week after week.',
                      'points': ['Correction Detective: recognize using a coaching correction.',
                                 'Great Teammate: celebrate encouraging or helping someone.',
                                 'Better Than Before: celebrate coach-confirmed personal improvement.',
                                 'A badge is recognition of its stated goal; skill mastery and competition readiness remain coaching decisions.']}),
            lesson('videos', 'Teach with examples and progress videos', 'Use the Video Library to make improvement visible.',
                ['Open Approved Skill Library inside Video Library. Upload a clearly labelled example with its event, skill name, and teaching notes.',
                 'Watch the ready example and explicitly approve it before using it as the gym’s reference.',
                 'Compare an athlete’s attempt with a matching approved example. Similar camera angles and a full-body view make comparison easier.',
                 'Open Athlete Progress, choose the athlete and skill, then compare their first and latest available attempts.',
                 'Use slow motion or Compare with first to review an older attempt. Drills and routines keep their own histories.'],
                [('Video Library', ('video_library:dashboard',)),
                 ('Approved Skill Library', ('video_library:skill_library',)),
                 ('Athlete Progress', ('video_library:video_progress',))], new=True),
            lesson('video-feedback', 'Show exactly what you mean', 'Add moment comments and drawings to the paused video.',
                ['Open a video or Skill Library example. Pause & comment selects the current video moment.',
                 'Draw on frame lets you use a pen, arrow, line, or circle. Undo stroke and Clear drawing adjust the draft.',
                 'Write one clear cue or next step, choose the audience, and Save moment. Tap a saved time to show that frame and its drawing.',
                 'New moment feedback starts as Only me. Choose Coaches, Athlete, or Athlete & parents intentionally; share the video first to enable family feedback.',
                 'Athletes and parents can view feedback already shared with them. They cannot edit your moment comments or drawings.'],
                [('Browse videos', ('video_library:video_list',)),
                 ('Approved Skill Library', ('video_library:skill_library',))], new=True),
            lesson('ready', 'You’re ready for practice', 'Keep Start Practice open during a busy session.',
                ['Choose the group, take attendance, and work through event rotations.',
                 'Finish practice when training ends, then review any remaining entries.',
                 'Revisit this walkthrough through Account Settings → Getting Started whenever you need it.'],
                [('Open Start Practice', ('practice_hub:start',))]),
        ]
    if role == 'athlete':
        plan = AthletePracticePlan.objects.filter(gym=gym, athlete=user,
            practice_date=timezone.localdate()).first()
        return [
            lesson('plan', 'See what you’re working on', 'Your coach gives you your own practice plan.',
                ['Open My Practice Plan to see today’s skills.',
                 'Ask your coach if a skill or target is missing.'],
                [('My Practice Plan', ('practice_focus:my_plan',))],
                'Today’s plan is ready' if plan else 'Your coach has not saved a plan for today yet'),
            lesson('track', 'Tap your result', 'Try these buttons. This practice demo does not save scores.',
                ['Choose the skill you just practiced.', 'Tap Wow, Hit, or Attempt.',
                 'Use Undo if you tap the wrong button. Ask your coach how they define a Wow for your skill.'],
                [('Open Skill Tracker', ('skill_tracker:tracker',))], demo=True),
            lesson('progress', 'See your progress', 'Your coach checks your results and shares feedback.',
                ['See your milestones and messages from your coach.',
                 'Your coach reviews your entries before they appear in parent progress reports.'],
                [('My Progress & Feedback', ('practice_focus:family_progress',)),
                 ('My dashboard', ('athlete_dashboard',))]),
            lesson('ready', 'Ready, set, practice', 'Ask your coach which event to start with.',
                ['Use your own account to record your practice.',
                 'Your coach helps you decide what to work on next.'],
                [('Open my plan', ('practice_focus:my_plan',)), ('Open Skill Tracker', ('skill_tracker:tracker',))]),
        ]
    approved = ParentAthleteLink.objects.filter(parent=user, approved=True,
        athlete__is_active=True, athlete__role='athlete', athlete__gym_memberships__gym=gym,
        athlete__gym_memberships__role='athlete', athlete__gym_memberships__is_active=True).distinct().count()
    pending = ParentAthleteLink.objects.filter(parent=user, approved=False,
        athlete__gym_memberships__gym=gym, athlete__gym_memberships__role='athlete',
        athlete__gym_memberships__is_active=True).distinct().count()
    status = f'{approved} approved child connection(s)' if approved else (
        'Your child connection is waiting for gym approval' if pending else 'Connect your child to see their information')
    return [
        lesson('connect', 'Connect with your child', 'Your gym checks and approves the connection.',
            ['Request a connection using your child’s name and date of birth.',
             'You will see child information once the gym approves access.'],
            [('Connect my child', ('connect_athlete', 'parents_portal:connect_athlete')),
             ('Parent dashboard', ('parent_dashboard', 'parents_portal:parent_dashboard'))], status),
        lesson('progress', 'Understand their progress', 'See skills, routines, milestones, and published weekly reports.',
            ['Reports use results approved by the coaching team.',
             'A practice target shows repetitions; meeting it does not automatically mean a skill is mastered.',
             'Only information for your approved child connections is shown.'],
            [('Weekly Reports & Feedback', ('practice_focus:family_progress',))]),
        lesson('feedback', 'Stay connected to the coach', 'Read shared feedback and ask questions through Messages.',
            ['Private coach notes stay private.', 'Notifications help you find new updates.',
             'Report emails become available after the gym configures delivery.'],
            [('Open Messages', ('communication_inbox',)), ('Open Notifications', ('notification_list',))]),
        lesson('ready', 'Make this your home for updates', 'Return to the parent dashboard whenever you need a quick overview.',
            ['Check the calendar for gym events.', 'Open Getting Started to revisit this guide.'],
            [('Parent dashboard', ('parent_dashboard', 'parents_portal:parent_dashboard'))], status),
    ]


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def getting_started(request):
    user = request.user
    if not user.is_active or user.role not in ROLES:
        raise PermissionDenied('This guide is for active gym accounts.')
    gym = member_gym(user)
    if gym is None:
        return render(request, 'practice_hub/onboarding_pending.html', {'home_url': dashboard(user)})
    steps = lessons(user, gym)
    progress = OnboardingProgress.objects.filter(user=user, gym=gym, role=user.role).first()
    step_keys = {step['key'] for step in steps}
    reviewed_keys = step_keys.intersection(progress.completed_steps if progress else [])
    missing_keys = step_keys - reviewed_keys
    guide_updated = bool(progress and progress.completed_at and missing_keys)
    default_index = (next(i for i, step in enumerate(steps) if step['key'] in missing_keys)
                     if guide_updated else progress.current_step if progress else 0)
    value = request.POST.get('step') if request.method == 'POST' else request.GET.get('step')
    try:
        index = int(value) if value is not None else default_index
        if not 0 <= index < len(steps):
            raise ValueError
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Choose a valid guide step.')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in ('next', 'back', 'later', 'restart', 'finish'):
            return HttpResponseBadRequest('Choose a valid guide action.')
        try:
            version = int(request.POST.get('version', '0'))
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Reload the guide before saving.')
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(pk=user.pk)
                progress, _ = OnboardingProgress.objects.get_or_create(user=user, gym=gym, role=user.role)
                if version != progress.version:
                    raise ValidationError('Your guide changed in another tab. Reload to continue from the saved step.')
                completed = set(progress.completed_steps)
                if step_keys - completed:
                    progress.completed_at = None
                if action == 'restart':
                    progress.completed_steps = []
                    progress.current_step = 0
                    progress.completed_at = None
                    progress.dismissed_at = None
                elif action == 'later':
                    progress.current_step = index
                    progress.dismissed_at = timezone.now()
                elif action == 'back':
                    progress.current_step = max(0, index - 1)
                    progress.dismissed_at = None
                else:
                    if request.POST.get('acknowledge') != 'yes':
                        raise ValidationError('Tick the box when you have reviewed this step.')
                    completed.add(steps[index]['key'])
                    progress.completed_steps = [s['key'] for s in steps if s['key'] in completed]
                    progress.dismissed_at = None
                    if action == 'finish':
                        if len(progress.completed_steps) != len(steps):
                            raise ValidationError('Review each step before finishing the guide.')
                        progress.completed_at = timezone.now()
                    progress.current_step = min(len(steps) - 1, index + 1)
                progress.version += 1
                progress.save()
            if action in ('later', 'finish'):
                messages.success(request, 'Guide saved for later.' if action == 'later' else 'Guide completed. You can revisit it from Getting Started.')
                return redirect(dashboard(user))
            return redirect('practice_hub:onboarding')
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
            return redirect('practice_hub:onboarding')
    completed = reviewed_keys
    for i, item in enumerate(steps):
        item['index'] = i
        item['done'] = item['key'] in completed
    return render(request, 'practice_hub/onboarding.html', {
        'gym': gym, 'progress': progress, 'steps': steps, 'step': steps[index], 'step_index': index,
        'last_step': index == len(steps) - 1, 'completed_count': len(completed),
        'home_url': dashboard(user), 'role_label': user.get_role_display(),
        'guide_complete': bool(progress and progress.completed_at and not missing_keys),
        'guide_updated': guide_updated, 'new_lesson_count': len(missing_keys),
    })


@login_required
@never_cache
@require_http_methods(['POST'])
def dismiss_guide(request):
    """Hide only this person's reminder, preserving their reviewed lessons."""
    user = request.user
    if not user.is_active or user.role not in ROLES:
        raise PermissionDenied('This guide is for active gym accounts.')
    gym = member_gym(user)
    if gym is None:
        request.session['practice_hub_dismissed_' + user.role] = True
    else:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)
            progress, _ = OnboardingProgress.objects.get_or_create(
                user=user, gym=gym, role=user.role)
            progress.dismissed_at = timezone.now()
            progress.version += 1
            progress.save(update_fields=['dismissed_at', 'version', 'updated_at'])
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'dismissed': True})
    destination = request.POST.get('next', '')
    if not destination.startswith('/') or not url_has_allowed_host_and_scheme(
            destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destination = dashboard(user)
    return redirect(destination)

