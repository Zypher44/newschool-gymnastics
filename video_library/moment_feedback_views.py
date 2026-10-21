import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import never_cache

from .models import Video, VideoMomentNote
from .moment_feedback import accessible_videos, visible_notes, clean_payload, serialize, can_manage
from .views import user_is_coach


def read_payload(request):
    if len(request.body) > 131072:
        raise ValueError('This drawing is too large. Simplify it before saving.')
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeError):
        raise ValueError('Feedback could not be read. Refresh and try again.')
    if not isinstance(data, dict):
        raise ValueError('Send a feedback object.')
    return data


def locked_video(user, video_id):
    allowed = accessible_videos(user).order_by().values('pk')
    video = get_object_or_404(Video.objects.select_for_update().filter(pk__in=allowed), pk=video_id)
    # Recheck access after acquiring the lock; sharing might have changed while waiting.
    get_object_or_404(accessible_videos(user), pk=video.pk)
    if video.status != Video.STATUS_READY or not video.video_file:
        raise ValueError('Wait for this video to finish processing before adding feedback.')
    return video


@login_required
@never_cache
def feedback_page(request, video_id):
    video = get_object_or_404(accessible_videos(request.user), pk=video_id)
    return render(request, 'video_library/video_moment_feedback.html', {
        'video': video, 'is_coach': user_is_coach(request.user),
        'library_url': reverse('video_library:dashboard' if user_is_coach(request.user)
                               else 'video_library:family_library'),
    })


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def moments(request, video_id):
    if request.method == 'GET':
        video = get_object_or_404(accessible_videos(request.user), pk=video_id)
        page = Paginator(visible_notes(video, request.user), 50).get_page(request.GET.get('page'))
        return JsonResponse(dict(notes=[serialize(note, request.user) for note in page],
                                 next_page=page.next_page_number() if page.has_next() else None))
    if not user_is_coach(request.user):
        return JsonResponse({'error': 'Only coaches can create moment feedback.'}, status=403)
    try:
        data = read_payload(request)
        with transaction.atomic():
            video = locked_video(request.user, video_id)
            fields = clean_payload(data, video)
            note = VideoMomentNote.objects.create(video=video, author=request.user, **fields)
        return JsonResponse({'note': serialize(note, request.user)}, status=201)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@login_required
@never_cache
@require_POST
def change_moment(request, video_id, note_id):
    if not user_is_coach(request.user):
        return JsonResponse({'error': 'Only coaches can change moment feedback.'}, status=403)
    try:
        data = read_payload(request)
        with transaction.atomic():
            video = locked_video(request.user, video_id)
            visible = visible_notes(video, request.user).order_by().values('pk')
            note = get_object_or_404(VideoMomentNote.objects.select_for_update().filter(pk__in=visible),
                                     pk=note_id, video=video)
            if not can_manage(note, request.user):
                return JsonResponse({'error': 'Only its author or head coach can change this feedback.'}, status=403)
            if data.get('updated_at') != note.updated_at.isoformat():
                return JsonResponse({'error': 'This feedback changed in another session. Reload it before editing.'}, status=409)
            if data.get('action') == 'delete':
                note.delete()
                return JsonResponse({'deleted': note_id})
            if data.get('action') != 'update':
                raise ValueError('Choose update or delete.')
            for field, value in clean_payload(data, video).items():
                setattr(note, field, value)
            note.save()
        return JsonResponse({'note': serialize(note, request.user)})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
