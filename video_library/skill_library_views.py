from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Video
from .analysis_queue import enqueue_analysis, ACTIVE_STATUSES
from .skill_library import approve, can_manage, is_approved, matching_skill_query, remove_approval
from .skill_library_forms import SkillExampleForm, SkillApprovalForm


def coach_library(view):
    @login_required
    @wraps(view)
    def guarded(request, *args, **kwargs):
        from .views import coach_gym_id
        if coach_gym_id(request.user) is None:
            return HttpResponseForbidden('An active coach membership in one gym is required.')
        return view(request, *args, **kwargs)
    return guarded


def accessible(user):
    from .views import get_accessible_videos
    return get_accessible_videos(user)


def locked_video(user, video_id):
    # The outer query has no DISTINCT or nullable joins, so PostgreSQL can lock it.
    video = get_object_or_404(Video.objects.select_for_update().filter(pk__in=accessible(user).order_by().values('pk')), pk=video_id)
    # Recheck after any lock wait; sharing may have changed in another request.
    if not accessible(user).filter(pk=video.pk).exists():
        raise Http404
    return video


def entry(user, video_id):
    return get_object_or_404(accessible(user).filter(is_skill_library_video=True), pk=video_id)


@coach_library
def library(request):
    videos = accessible(request.user).filter(is_skill_library_video=True).exclude(status=Video.STATUS_ARCHIVED)
    state = request.GET.get('state', 'approved')
    if state not in ('approved', 'pending', 'all'):
        state = 'approved'
    valid = Q(is_coaching_example=True, skill_library_approved_by__isnull=False, skill_library_approved_at__isnull=False)
    counts = {'approved': videos.filter(valid, status=Video.STATUS_READY).count(),
              'pending': videos.exclude(valid & Q(status=Video.STATUS_READY)).count(), 'all': videos.count()}
    if state == 'approved':
        videos = videos.filter(valid, status=Video.STATUS_READY)
    elif state == 'pending':
        videos = videos.exclude(valid & Q(status=Video.STATUS_READY))
    event = request.GET.get('event', '')
    if event in dict(Video.EVENT_CHOICES):
        videos = videos.filter(event=event)
    else:
        event = ''
    query = request.GET.get('q', '').strip()[:150]
    if query:
        videos = videos.filter(Q(title__icontains=query) | Q(skill_name__icontains=query))
    attempt = None
    attempt_id = request.GET.get('attempt')
    if attempt_id:
        attempt = get_object_or_404(accessible(request.user), pk=attempt_id if str(attempt_id).isdigit() else 0)
        videos = videos.filter(event=attempt.event).filter(matching_skill_query(attempt.skill_name))
    videos = videos.select_related('skill_library_approved_by').order_by('event', 'skill_name', '-uploaded_at', 'pk')
    page = Paginator(videos, 12).get_page(request.GET.get('page'))
    parameters = request.GET.copy(); parameters.pop('page', None)
    return render(request, 'video_library/skill_library.html', {'page_obj': page, 'state': state, 'counts': counts,
                  'event': event, 'q': query, 'events': Video.EVENT_CHOICES, 'attempt': attempt,
                  'filter_query': parameters.urlencode()})


@coach_library
def upload(request):
    from .views import coach_gym_id
    form = SkillExampleForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None,
                            initial={'event': request.GET.get('event', ''), 'skill_name': request.GET.get('skill', '')[:150]})
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data; file = data['video']
        with transaction.atomic():
            video = Video.objects.create(gym_id=coach_gym_id(request.user), uploaded_by=request.user,
                title=data['title'], event=data['event'], skill_name=data['skill_name'], camera_view=data['camera_view'],
                notes=data['notes'].strip(), video_file=file, original_filename=file.name,
                content_type=getattr(file, 'content_type', ''), file_size_bytes=file.size,
                video_type=Video.TYPE_DRILL, visibility=Video.VISIBILITY_COACHES,
                is_skill_library_video=True, is_coaching_example=False, status=Video.STATUS_UPLOADING)
            if data['analyze']:
                enqueue_analysis(video, request.user)
        messages.success(request, 'Skill example uploaded. Once processing finishes, watch it and approve it for the library.')
        return redirect('video_library:skill_example_detail', video_id=video.pk)
    names = accessible(request.user).exclude(skill_name='').values_list('skill_name', flat=True).order_by('skill_name').distinct()
    return render(request, 'video_library/skill_example_form.html', {'form': form, 'skill_names': names, 'editing': False})


@coach_library
def detail(request, video_id):
    video = entry(request.user, video_id)
    attempts = accessible(request.user).filter(status=Video.STATUS_READY, event=video.event,
                    is_skill_library_video=False).filter(matching_skill_query(video.skill_name))
    attempts = attempts.filter(Q(primary_athlete__isnull=False) | Q(tagged_athletes__isnull=False)).exclude(pk=video.pk).distinct().order_by('-uploaded_at', 'pk')
    analysis = video.analyses.order_by('-created_at', '-pk').first()
    return render(request, 'video_library/skill_example_detail.html', {'video': video, 'approved': is_approved(video),
                  'can_manage': can_manage(video, request.user), 'attempts': attempts, 'analysis': analysis,
                  'approval_form': SkillApprovalForm()})


@coach_library
def edit(request, video_id):
    video = entry(request.user, video_id)
    if not can_manage(video, request.user):
        return HttpResponseForbidden('Only the uploader, approving coach or head coach can edit this example.')
    initial = {name: getattr(video, name) for name in ('title', 'event', 'skill_name', 'camera_view', 'notes')}
    initial['analyze'] = False
    form = SkillExampleForm(request.POST if request.method == 'POST' else None, initial=initial, editing=True)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            video = locked_video(request.user, video_id)
            if not video.is_skill_library_video or not can_manage(video, request.user):
                return HttpResponseForbidden('This example cannot be edited by your account.')
            changed = any(getattr(video, name) != data[name] for name in ('event', 'skill_name', 'camera_view'))
            if changed and video.analyses.filter(status__in=ACTIVE_STATUSES).exists():
                form.add_error(None, 'Wait for the current analysis to finish before changing the event, skill or camera view.')
            else:
                for name in ('title', 'event', 'skill_name', 'camera_view', 'notes'):
                    setattr(video, name, data[name])
                video.save(update_fields=['title', 'event', 'skill_name', 'camera_view', 'notes', 'updated_at'])
                if changed:
                    remove_approval(video)
                if data['analyze']:
                    if video.status not in (Video.STATUS_FAILED, Video.STATUS_ARCHIVED):
                        enqueue_analysis(video, request.user)
                    else:
                        messages.info(request, 'The video must finish processing before a new analysis can run.')
                messages.success(request, 'Example updated.' + (' Review and approve it again after changing its event, skill or camera view.' if changed else ''))
                return redirect('video_library:skill_example_detail', video_id=video.pk)
    names = accessible(request.user).exclude(skill_name='').values_list('skill_name', flat=True).order_by('skill_name').distinct()
    return render(request, 'video_library/skill_example_form.html', {'form': form, 'skill_names': names, 'editing': True, 'video': video})


@coach_library
@require_POST
def add_existing(request, video_id):
    with transaction.atomic():
        video = locked_video(request.user, video_id)
        if not video.is_skill_library_video:
            video.is_skill_library_video = True
            video.save(update_fields=['is_skill_library_video', 'updated_at'])
    messages.success(request, 'Video added for skill-library review. Approval is a separate step.')
    return redirect('video_library:skill_example_detail', video_id=video.pk)


@coach_library
@require_POST
def approval(request, video_id):
    form = SkillApprovalForm(request.POST)
    with transaction.atomic():
        video = locked_video(request.user, video_id)
        if not form.is_valid():
            messages.error(request, 'Confirm that you reviewed this video before approving it.')
        elif is_approved(video):
            messages.info(request, 'This example is already approved.')
        else:
            try:
                approve(video, request.user)
            except ValueError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, 'Approved skill example added to the library.')
    if video.is_skill_library_video:
        return redirect('video_library:skill_example_detail', video_id=video.pk)
    return redirect('video_library:video_detail', video_id=video.pk)


@coach_library
@require_POST
def remove(request, video_id):
    with transaction.atomic():
        video = locked_video(request.user, video_id)
        if not can_manage(video, request.user):
            return HttpResponseForbidden('Only the uploader, approving coach or head coach can remove this example.')
        remove_approval(video, remove_from_library=True)
    messages.success(request, 'Removed from the skill library. The original video remains in Video Library.')
    return redirect('video_library:skill_library')


def toggle_existing_example(request, video_id):
    """Compatibility for the existing explicit Mark Coaching Example button."""
    from .views import coach_gym_id
    if coach_gym_id(request.user) is None:
        return HttpResponseForbidden('An active coach membership is required.')
    with transaction.atomic():
        video = locked_video(request.user, video_id)
        if is_approved(video):
            if not can_manage(video, request.user):
                return HttpResponseForbidden('Only the uploader, approving coach or head coach can remove approval.')
            remove_approval(video)
            messages.success(request, 'Approval removed. This example is awaiting approval in the skill library.')
        else:
            try:
                approve(video, request.user)
            except ValueError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, 'Approved skill example added to the library.')
    return redirect('video_library:video_detail', video_id=video.pk)
