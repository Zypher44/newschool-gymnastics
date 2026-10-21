"""Approved gym examples, with the same permissions as the video library."""
from .models import Video
from .skill_library import approved_examples, matching_skill_query


def get_coaching_examples(video, user):
    if not video or not getattr(user, 'is_authenticated', False) or not (video.skill_name or '').strip() or not video.event:
        return Video.objects.none()
    from .views import get_accessible_videos
    if not get_accessible_videos(user).filter(pk=video.pk).exists():
        return Video.objects.none()
    return (approved_examples(user).filter(gym_id=video.gym_id, event=video.event)
            .filter(matching_skill_query(video.skill_name)).exclude(pk=video.pk)
            .prefetch_related(None).order_by('-skill_library_approved_at', '-uploaded_at', 'pk'))
