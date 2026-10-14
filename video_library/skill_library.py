"""Gym-scoped approved examples, distinct from athlete reference attempts."""
from django.db.models import Q
from django.utils import timezone
from .models import Video
from .ai.skill_interpretation import normalize_skill_name, SKILL_ALIASES


def matching_skill_query(name):
    canonical = normalize_skill_name(name)
    names = {name.strip(), canonical}
    names.update(alias for alias, target in SKILL_ALIASES.items() if target == canonical)
    query = Q(pk__in=[])
    for candidate in names:
        query |= Q(skill_name__iexact=candidate)
    return query


def is_approved(video):
    return video.is_approved_skill_example


def approved_examples(user):
    from .views import get_accessible_videos
    return (get_accessible_videos(user).filter(is_skill_library_video=True, is_coaching_example=True,
                skill_library_approved_by__isnull=False, skill_library_approved_at__isnull=False,
                status=Video.STATUS_READY).exclude(video_file='').exclude(video_file__isnull=True)
            .select_related('skill_library_approved_by'))


def can_manage(video, user):
    return bool(user.role == 'head_coach' or video.uploaded_by_id == user.pk or video.skill_library_approved_by_id == user.pk)


def approve(video, coach):
    if video.status != Video.STATUS_READY or not video.video_file or not video.event or not video.skill_name.strip():
        raise ValueError('The video must finish processing and have an event and skill before it can be approved.')
    video.is_skill_library_video = True
    video.is_coaching_example = True
    video.skill_library_approved_by = coach
    video.skill_library_approved_at = timezone.now()
    video.save(update_fields=['is_skill_library_video', 'is_coaching_example', 'skill_library_approved_by', 'skill_library_approved_at', 'updated_at'])


def remove_approval(video, *, remove_from_library=False):
    video.is_coaching_example = False
    video.skill_library_approved_by = None
    video.skill_library_approved_at = None
    video.is_skill_library_video = not remove_from_library
    video.save(update_fields=['is_skill_library_video', 'is_coaching_example', 'skill_library_approved_by', 'skill_library_approved_at', 'updated_at'])
