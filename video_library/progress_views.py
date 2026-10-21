"""Video progress history; all selections remain within the viewer's video access."""
from collections import defaultdict
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from gyms.models import GymMembership
from parents_portal.access import get_approved_parent_links, get_parent_gym_ids

from .models import Video
from .views import coach_gym_id, get_accessible_videos, user_is_coach


def athletes_for(user):
    User = get_user_model()
    athletes = User.objects.filter(role='athlete', is_active=True)
    memberships = dict(gym_memberships__role='athlete', gym_memberships__is_active=True,
                       gym_memberships__gym__is_active=True)
    if user_is_coach(user):
        gym_id = coach_gym_id(user)
        if gym_id is None:
            return athletes.none()
        athletes = athletes.filter(gym_memberships__gym_id=gym_id, **memberships)
        if user.role == 'coach':
            videos = get_accessible_videos(user)
            athletes = athletes.filter(
                Q(pk__in=videos.values('primary_athlete_id')) |
                Q(pk__in=videos.values('tagged_athletes__pk')) |
                Q(pk__in=user.assigned_athletes.values('athlete_id')) |
                Q(practice_groups__coaches=user, practice_groups__gym_id=gym_id,
                  practice_groups__is_active=True)
            )
    elif user.role == 'athlete':
        athletes = athletes.filter(pk=user.pk, **memberships)
    elif user.role == 'parent':
        athletes = athletes.filter(pk__in=get_approved_parent_links(user).values('athlete_id'))
    else:
        return athletes.none()
    return athletes.distinct().order_by('first_name', 'last_name', 'username', 'pk')


def attempt_videos(user, athlete):
    if user_is_coach(user):
        videos = get_accessible_videos(user)
    else:
        gyms = GymMembership.objects.filter(user=athlete, role='athlete', is_active=True,
                                            gym__is_active=True)
        if user.role == 'parent':
            gyms = gyms.filter(gym_id__in=get_parent_gym_ids(user))
        visibility = [Video.VISIBILITY_PARENTS]
        if user.role == 'athlete':
            visibility.append(Video.VISIBILITY_ATHLETE)
        videos = Video.objects.filter(gym_id__in=gyms.values('gym_id'), visibility__in=visibility)
    return (videos.filter(Q(primary_athlete=athlete) | Q(tagged_athletes=athlete),
                          status=Video.STATUS_READY, is_skill_library_video=False,
                          is_coaching_example=False)
            .exclude(video_file='').select_related('primary_athlete', 'training_group')
            .prefetch_related(None).defer('ai_results', 'ai_summary', 'notes', 'processing_error')
            .distinct())


def normalized_skill(name):
    return ' '.join((name or '').split()).casefold()


def kind_for(video):
    if video.video_type in (Video.TYPE_ROUTINE, Video.TYPE_MOCK_MEET):
        return 'routine'
    return 'drill' if video.video_type == Video.TYPE_DRILL else 'skill'


def dated(video):
    return video.recorded_at or video.uploaded_at


def timeline_url(athlete, key, **extra):
    event, skill, kind = key
    query = dict(event=event, skill=skill, kind=kind, **extra)
    return reverse('video_library:athlete_timeline', args=[athlete.pk]) + '?' + urlencode(query)


def can_open(user):
    return user_is_coach(user) or user.role in ('athlete', 'parent')


@login_required
def index(request):
    if not can_open(request.user):
        return HttpResponseForbidden('Video progress is available to coaches, athletes and parents.')
    athletes = athletes_for(request.user)
    query = request.GET.get('q', '').strip()[:150]
    if query:
        athletes = athletes.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)
                                   | Q(username__icontains=query))
    return render(request, 'video_library/video_progress_index.html', {
        'page_obj': Paginator(athletes, 24).get_page(request.GET.get('page')),
        'query': query, 'query_string': urlencode({'q': query}),
        'is_coach': user_is_coach(request.user),
        'library_url': reverse('video_library:dashboard' if user_is_coach(request.user)
                               else 'video_library:family_library'),
    })


@login_required
def timeline(request, athlete_id):
    if not can_open(request.user):
        return HttpResponseForbidden('Video progress is available to coaches, athletes and parents.')
    athlete = get_object_or_404(athletes_for(request.user), pk=athlete_id)
    videos = list(attempt_videos(request.user, athlete))
    # Recorded date is the actual training date. Older uploads without it use upload date.
    videos.sort(key=lambda video: (dated(video), video.uploaded_at, video.pk))
    grouped = defaultdict(list)
    for video in videos:
        video.progress_date = dated(video)
        video.progress_date_source = 'Recorded' if video.recorded_at else 'Uploaded'
        grouped[(video.event, normalized_skill(video.skill_name), kind_for(video))].append(video)
    event = request.GET.get('event', '').strip()
    if event and event not in dict(Video.EVENT_CHOICES):
        raise Http404('Unknown event.')
    sections = []
    for key, attempts in grouped.items():
        if event and key[0] != event:
            continue
        first, latest = attempts[0], attempts[-1]
        label = ' '.join((latest.skill_name or '').split())
        if not label:
            label = 'Full routine' if key[2] == 'routine' else 'Unlabelled videos'
        sections.append(dict(key=key, label=label, event=latest.get_event_display(), kind=key[2],
                             count=len(attempts), first=first, latest=latest,
                             url=timeline_url(athlete, key)))
    sections.sort(key=lambda section: (dated(section['latest']), section['latest'].pk), reverse=True)
    skill = normalized_skill(request.GET.get('skill', ''))
    kind = request.GET.get('kind', '').strip()
    selected = None
    if 'skill' in request.GET or kind:
        candidates = [section for section in sections if section['key'][1] == skill
                      and (not kind or section['kind'] == kind)]
        if not candidates:
            raise Http404('No accessible attempts for this skill.')
        selected = candidates[0]
    elif sections:
        selected = sections[0]
    comparison = None
    chosen = []
    if selected:
        chosen = grouped[selected['key']]
        first = chosen[0]
        current = chosen[-1]
        requested = request.GET.get('compare', '').strip()
        if requested:
            current = next((video for video in chosen if str(video.pk) == requested), None)
            if current is None:
                raise Http404('That comparison attempt is unavailable.')
        # Blank skill labels are ambiguous; full routines are identified by their event.
        comparable = bool(selected['key'][1]) or selected['kind'] == 'routine'
        selected['comparable'] = comparable
        if first.pk != current.pk and comparable:
            comparison = dict(first=first, current=current, is_latest=current.pk == chosen[-1].pk,
                              camera_warning=first.camera_view != current.camera_view
                              or first.camera_view != 'side')
        for video in chosen:
            video.compare_with_first_url = (timeline_url(athlete, selected['key'], compare=video.pk)
                                            if comparable and video.pk != first.pk else '')
        selected['url'] = timeline_url(athlete, selected['key'])
    elif request.GET.get('compare'):
        raise Http404('Choose a skill before comparing.')
    page = Paginator(chosen, 12).get_page(request.GET.get('page'))
    page_query = dict(event=event)
    if selected:
        page_query.update(event=selected['key'][0], skill=selected['key'][1], kind=selected['key'][2])
    if request.GET.get('compare'):
        page_query['compare'] = request.GET['compare']
    base_page_url = reverse('video_library:athlete_timeline', args=[athlete.pk]) + '?' + urlencode(page_query)
    return render(request, 'video_library/athlete_progress_timeline.html', {
        'athlete': athlete, 'sections': sections, 'selected': selected,
        'comparison': comparison, 'page_obj': page, 'total_video_count': len(videos),
        'event_choices': Video.EVENT_CHOICES, 'event_filter': event,
        'is_coach': user_is_coach(request.user), 'page_url': base_page_url,
        'library_url': reverse('video_library:dashboard' if user_is_coach(request.user)
                               else 'video_library:family_library'),
    })
