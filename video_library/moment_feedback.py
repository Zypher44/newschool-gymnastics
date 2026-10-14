"""Access and validation for manually created video feedback. No AI or image API."""
from decimal import Decimal, ROUND_HALF_UP
import math

from django.db.models import F, Q
from gyms.models import GymMembership
from parents_portal.access import get_approved_parent_athlete_ids, get_parent_gym_ids

from .models import Video, VideoMomentNote
from .views import get_accessible_videos, user_is_coach

COLORS = {'#ef4444', '#facc15', '#3b82f6', '#22c55e'}
TOOLS = {'pen', 'line', 'arrow', 'circle'}


def accessible_videos(user):
    if user_is_coach(user):
        return get_accessible_videos(user)
    if user.role == 'parent':
        athletes = get_approved_parent_athlete_ids(user)
        gyms = get_parent_gym_ids(user)
        visibility = [Video.VISIBILITY_PARENTS]
        participant = (
            Q(primary_athlete_id__in=athletes,
              primary_athlete__gym_memberships__gym_id=F('gym_id'),
              primary_athlete__gym_memberships__role='athlete',
              primary_athlete__gym_memberships__is_active=True) |
            Q(tagged_athletes__id__in=athletes,
              tagged_athletes__gym_memberships__gym_id=F('gym_id'),
              tagged_athletes__gym_memberships__role='athlete',
              tagged_athletes__gym_memberships__is_active=True)
        )
    elif user.role == 'athlete':
        athletes = [user.pk]
        gyms = GymMembership.objects.filter(user=user, role='athlete', is_active=True,
                                            gym__is_active=True).values('gym_id')
        visibility = [Video.VISIBILITY_ATHLETE, Video.VISIBILITY_PARENTS]
        participant = Q(primary_athlete_id__in=athletes) | Q(tagged_athletes__id__in=athletes)
    else:
        return Video.objects.none()
    return (Video.objects.filter(gym_id__in=gyms, visibility__in=visibility, status=Video.STATUS_READY)
            .filter(participant)
            .exclude(video_file='').distinct())


def visible_notes(video, user):
    notes = VideoMomentNote.objects.filter(video=video).select_related('author')
    if user_is_coach(user):
        return notes.filter(Q(author=user) | ~Q(visibility=Video.VISIBILITY_PRIVATE))
    if user.role == 'athlete':
        return notes.filter(visibility__in=[Video.VISIBILITY_ATHLETE, Video.VISIBILITY_PARENTS])
    if user.role == 'parent':
        return notes.filter(visibility=Video.VISIBILITY_PARENTS)
    return notes.none()


def can_manage(note, user):
    return user_is_coach(user) and (note.author_id == user.pk or
           (user.role == 'head_coach' and note.visibility != Video.VISIBILITY_PRIVATE))


def number(value):
    try:
        finite = isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        finite = False
    if isinstance(value, bool) or not finite:
        raise ValueError('Drawing coordinates must be finite numbers.')
    if not 0 <= value <= 1:
        raise ValueError('Drawing coordinates must stay within the video frame.')
    return round(value, 6)


def clean_drawing(value):
    if not isinstance(value, list) or len(value) > 50:
        raise ValueError('Use at most 50 drawing shapes per moment.')
    output, total = [], 0
    for shape in value:
        if not isinstance(shape, dict) or set(shape) != {'tool', 'color', 'points'}:
            raise ValueError('Invalid drawing shape.')
        tool, color, points = shape['tool'], shape['color'], shape['points']
        if not isinstance(tool, str) or tool not in TOOLS or not isinstance(color, str) or color not in COLORS:
            raise ValueError('Choose a supported drawing tool and color.')
        if not isinstance(points, list) or not 2 <= len(points) <= 400:
            raise ValueError('Each shape needs 2 to 400 points.')
        if tool != 'pen' and len(points) != 2:
            raise ValueError('Lines, arrows and circles need exactly two points.')
        total += len(points)
        if total > 5000:
            raise ValueError('This drawing has too many points. Simplify it and save again.')
        cleaned = []
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError('Invalid drawing point.')
            cleaned.append([number(point[0]), number(point[1])])
        output.append(dict(tool=tool, color=color, points=cleaned))
    return output


def clean_payload(data, video):
    if not isinstance(data, dict):
        raise ValueError('Send a feedback object.')
    raw_time = data.get('timestamp_seconds')
    if isinstance(raw_time, bool) or not isinstance(raw_time, (int, float, str)):
        raise ValueError('Choose a valid video moment.')
    try:
        timestamp = float(raw_time)
    except (ValueError, OverflowError):
        raise ValueError('Choose a valid video moment.')
    if not math.isfinite(timestamp) or not 0 <= timestamp <= 21600:
        raise ValueError('Choose a valid video moment within six hours.')
    duration = video.duration_seconds
    if duration is not None and duration > 0 and timestamp > float(duration) + 0.05:
        raise ValueError('That moment is beyond the end of this video.')
    timestamp = Decimal(str(timestamp)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    comment = data.get('comment', '')
    if not isinstance(comment, str) or len(comment) > 2500:
        raise ValueError('Keep comments to 2,500 characters.')
    comment = comment.strip()
    drawing = clean_drawing(data.get('drawing', []))
    if not comment and not drawing:
        raise ValueError('Add a comment or a drawing before saving.')
    visibility = data.get('visibility', Video.VISIBILITY_PRIVATE)
    if not isinstance(visibility, str) or visibility not in {Video.VISIBILITY_PRIVATE, Video.VISIBILITY_COACHES,
                           Video.VISIBILITY_ATHLETE, Video.VISIBILITY_PARENTS}:
        raise ValueError('Choose a valid sharing option.')
    if visibility == Video.VISIBILITY_ATHLETE and video.visibility not in (
            Video.VISIBILITY_ATHLETE, Video.VISIBILITY_PARENTS):
        raise ValueError('Share the video with the athlete before sharing its moment feedback.')
    if visibility == Video.VISIBILITY_PARENTS and video.visibility != Video.VISIBILITY_PARENTS:
        raise ValueError('Share the video with parents before sharing its moment feedback.')
    return dict(timestamp_seconds=timestamp, comment=comment, drawing=drawing, visibility=visibility)


def serialize(note, user):
    return dict(id=note.pk, timestamp_seconds=float(note.timestamp_seconds), comment=note.comment,
                drawing=note.drawing, visibility=note.visibility,
                author=note.author.get_full_name() or note.author.username if note.author else 'Former coach',
                updated_at=note.updated_at.isoformat(), can_edit=can_manage(note, user))
