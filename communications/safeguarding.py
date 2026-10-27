"""Application guardrails, not certification of an adult's age or screening."""
from django.db.models import Q, F
from django.urls import reverse

from accounts.models import User
from gyms.models import GymMembership
from gyms.tenant import single_active_gym_id
from parents_portal.models import ParentAthleteLink
from .models import Conversation, Notification

STAFF_ROLES = ('director', 'head_coach', 'coach')
OBSERVER_ROLES = ('head_coach', 'coach')


def active_members(gym_id):
    return User.objects.filter(is_active=True, gym_memberships__gym_id=gym_id,
        gym_memberships__gym__is_active=True, gym_memberships__is_active=True,
        role=F('gym_memberships__role'),
        gym_memberships__role__in=STAFF_ROLES + ('athlete', 'parent')).distinct()


def athlete_in_pair(first, second):
    athletes = [u for u in (first, second) if u.role == 'athlete']
    return athletes[0] if len(athletes) == 1 else None


def eligible_observers(first, second):
    gym_id = single_active_gym_id(first, [first.role])
    athlete = athlete_in_pair(first, second)
    if gym_id is None or athlete is None:
        return User.objects.none()
    parent_ids = ParentAthleteLink.objects.filter(athlete=athlete, approved=True).values('parent_id')
    return active_members(gym_id).filter(
        Q(role__in=OBSERVER_ROLES, gym_memberships__role__in=OBSERVER_ROLES) |
        Q(role='parent', gym_memberships__role='parent', pk__in=parent_ids),
    ).exclude(pk__in=[first.pk, second.pk]).order_by('role', 'first_name', 'username').distinct()


def supervised_pair(first, second, observer):
    athlete = athlete_in_pair(first, second)
    if athlete and next(u for u in (first, second) if u.pk != athlete.pk).role not in OBSERVER_ROLES:
        raise PermissionError('Athlete conversations are with coaches only. Parents can contact directors.')
    if athlete and (observer is None or not eligible_observers(first, second).filter(pk=observer.pk).exists()):
        raise PermissionError('Athlete messages need an explicitly selected approved linked parent or second coach. No message has been sent.')
    if not athlete and observer is not None:
        raise PermissionError('An observer can be added here only for an athlete conversation.')
    return athlete


def can_view_conversation(user, conversation):
    if not user.is_authenticated or not user.is_active:
        return False
    if conversation.gym_id != single_active_gym_id(user, [user.role]):
        return False
    if not conversation.participants.filter(pk=user.pk).exists():
        return False
    if user.role == 'parent' and conversation.related_athlete_id:
        if not ParentAthleteLink.objects.filter(parent=user, athlete_id=conversation.related_athlete_id, approved=True).exists():
            return False
    if conversation.supervision_observer_id == user.pk:
        if not conversation.requires_supervision or not conversation.related_athlete_id:
            return False
        # A staff observer must still be staff; a parent must still have approval.
        if user.role not in STAFF_ROLES + ('parent',):
            return False
    return True


def supervision_error(conversation):
    people = list(conversation.participants.all())
    athletes = [u for u in people if u.role == 'athlete']
    if not athletes and not conversation.requires_supervision:
        return ''
    if not conversation.requires_supervision:
        return 'This earlier athlete conversation is read-only. Start a new supervised conversation; earlier messages will not be shared with a new observer.'
    if len(athletes) != 1 or conversation.related_athlete_id != athletes[0].pk:
        return 'This conversation needs a new supervised thread before messages can continue.'
    observer = next((p for p in people if p.pk == conversation.supervision_observer_id), None)
    others = [p for p in people if p.pk not in (athletes[0].pk, conversation.supervision_observer_id)]
    if observer is None or len(others) != 1 or len(people) != 3:
        return 'The observer is unavailable. Start a new supervised conversation.'
    if others[0].role not in OBSERVER_ROLES:
        return 'Athletes message coaches only. This earlier conversation is read-only; parents can contact directors.'
    if not eligible_observers(athletes[0], others[0]).filter(pk=observer.pk).exists():
        return 'The observer no longer has approved access. Start a new supervised conversation.'
    for person in people:
        if not person.is_active or not GymMembership.objects.filter(user=person,
                gym_id=conversation.gym_id, gym__is_active=True, role=person.role, is_active=True).exists():
            return 'A participant no longer has active gym access. Start a new supervised conversation.'
    return ''


def visible_conversation_ids(user):
    if not user.is_authenticated or not user.is_active:
        return []
    rows = Conversation.objects.filter(gym_id=single_active_gym_id(user, [user.role]), participants=user).exclude(gym__isnull=True)
    if user.role == 'parent':
        linked = ParentAthleteLink.objects.filter(parent=user, approved=True).values('athlete_id')
        rows = rows.filter(Q(related_athlete__isnull=True) | Q(related_athlete_id__in=linked))
    if user.role not in STAFF_ROLES + ('parent',):
        rows = rows.exclude(supervision_observer=user)
    return list(rows.values_list('pk', flat=True).distinct())


def visible_notifications(user, queryset):
    # A revoked parent connection must not leave message previews in the bell/inbox.
    prefix = reverse('conversation_detail', args=[0]).rsplit('0/', 1)[0]
    links = [reverse('conversation_detail', args=[pk]) for pk in visible_conversation_ids(user)]
    return queryset.exclude(Q(notification_type=Notification.TYPE_MESSAGE, link__startswith=prefix) & ~Q(link__in=links))
