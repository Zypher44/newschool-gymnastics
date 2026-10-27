from django.db import transaction
from django.db.models import Q, F
from django.urls import reverse

from accounts.models import User
from coaches.models import CoachAthleteAssignment
from parents_portal.models import ParentAthleteLink

from .models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)

from gyms.models import GymMembership, TrainingGroupAthlete, TrainingGroupCoach
from gyms.tenant import single_active_gym_id


def create_notification(
    *,
    recipient,
    title,
    message='',
    notification_type=Notification.TYPE_GENERAL,
    sender=None,
    link=''
):
    if recipient is None:
        return None

    if recipient.role == 'parent' and notification_type not in (Notification.TYPE_MESSAGE, Notification.TYPE_SYSTEM):
        from accounts.models import CommunicationPreference
        if CommunicationPreference.objects.filter(user=recipient, in_app_updates=False).exists():
            return None

    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )


def create_notifications_for_users(
    *,
    recipients,
    title,
    message='',
    notification_type=Notification.TYPE_GENERAL,
    sender=None,
    link=''
):
    notifications = []

    unique_recipients = {
        recipient.id: recipient
        for recipient in recipients
        if recipient is not None
    }

    for recipient in unique_recipients.values():
        notification = create_notification(
            recipient=recipient,
            sender=sender,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )

        if notification:
            notifications.append(notification)

    return notifications


def get_display_name(user):
    full_name = user.get_full_name().strip()

    if full_name:
        return full_name

    return user.username


def get_coaches_for_athlete(athlete):
    gym_id = single_active_gym_id(athlete, ['athlete'])
    direct = CoachAthleteAssignment.objects.filter(athlete=athlete).values('coach_id')
    groups = TrainingGroupAthlete.objects.filter(athlete=athlete, is_active=True,
        group__gym_id=gym_id, group__is_active=True).values('group_id')
    group_coaches = TrainingGroupCoach.objects.filter(group_id__in=groups).values('coach_id')
    return User.objects.filter(Q(pk__in=direct) | Q(pk__in=group_coaches),
        is_active=True, role__in=['coach', 'head_coach'], gym_memberships__gym_id=gym_id,
        gym_memberships__role__in=['coach', 'head_coach'], gym_memberships__is_active=True).distinct()

def get_parents_for_athlete(athlete):
    parent_ids = ParentAthleteLink.objects.filter(
        athlete=athlete, approved=True
    ).values_list(
        'parent_id',
        flat=True
    )

    return User.objects.filter(
        id__in=parent_ids,
        role='parent'
    ).distinct()

def get_athletes_for_coach(coach):
    gym_id = single_active_gym_id(coach, ['coach', 'head_coach'])
    if gym_id is None:
        return User.objects.none()
    if coach.role == 'head_coach':
        return User.objects.filter(
            role='athlete', gym_memberships__gym_id=gym_id,
            gym_memberships__role='athlete', gym_memberships__is_active=True,
        ).order_by(
            'first_name',
            'username'
        )

    athlete_ids = CoachAthleteAssignment.objects.filter(
        coach=coach
    ).values_list(
        'athlete_id',
        flat=True
    )

    return User.objects.filter(
        id__in=athlete_ids,
        role='athlete', gym_memberships__gym_id=gym_id,
        gym_memberships__role='athlete', gym_memberships__is_active=True,
    ).order_by(
        'first_name',
        'username'
    )

def _get_allowed_message_recipients(user):
    """
    Return users that the current user may message.

    Directors may message active members belonging to their gym.
    """

    gym_id = single_active_gym_id(user, [user.role])
    if gym_id is None or not user.is_active:
        return User.objects.none()

    if user.role == 'director':
        director_membership = (
            GymMembership.objects
            .filter(
                user=user,
                role='director',
                is_active=True, gym_id=gym_id, gym__is_active=True,
            )
            .select_related('gym')
            .first()
        )

        if not director_membership:
            return User.objects.none()

        recipient_ids = (
            GymMembership.objects
            .filter(
                gym=director_membership.gym,
                is_active=True,
                role__in=[
                    'head_coach',
                    'coach',
                    'parent',
                ]
            )
            .exclude(user=user)
            .values_list(
                'user_id',
                flat=True
            )
        )

        return (
            User.objects
            .filter(id__in=recipient_ids, is_active=True)
            .exclude(id=user.id)
            .distinct()
            .order_by(
                'role',
                'first_name',
                'last_name',
                'username'
            )
        )

    if user.role in ['head_coach', 'coach']:
        return (
            User.objects
            .exclude(id=user.id)
            .filter(is_active=True,
                gym_memberships__gym_id=gym_id,
                gym_memberships__role__in=['director', 'coach', 'head_coach', 'athlete', 'parent'],
                gym_memberships__is_active=True,
                role__in=[
                    'director',
                    'coach',
                    'head_coach',
                    'athlete',
                    'parent',
                ]
            )
            .distinct()
            .order_by(
                'role',
                'first_name',
                'username'
            )
        )

    if user.role == 'athlete':
        coach_ids = get_coaches_for_athlete(user).values('pk')
        return User.objects.filter(pk__in=coach_ids,
            is_active=True, gym_memberships__gym_id=gym_id,
            gym_memberships__is_active=True).exclude(pk=user.pk).distinct()

    if user.role == 'parent':
        linked_athlete_ids = (
            ParentAthleteLink.objects
            .filter(
                parent=user,
                approved=True, athlete__is_active=True,
                athlete__gym_memberships__gym_id=gym_id,
                athlete__gym_memberships__role='athlete',
                athlete__gym_memberships__is_active=True,
            )
            .values_list(
                'athlete_id',
                flat=True
            )
        )

        coach_ids = set()
        for athlete in User.objects.filter(pk__in=linked_athlete_ids, role='athlete', is_active=True):
            coach_ids.update(get_coaches_for_athlete(athlete).values_list('pk', flat=True))

        director_ids = GymMembership.objects.filter(
            gym_id=gym_id, role='director', is_active=True,
        ).values_list('user_id', flat=True)
        return (
            User.objects
            .filter(
                id__in=list(coach_ids) + list(director_ids), is_active=True,
                gym_memberships__gym_id=gym_id,
                gym_memberships__is_active=True,
                role__in=[
                    'director',
                    'coach',
                    'head_coach',
                ]
            )
            .distinct()
            .order_by(
                'first_name',
                'username'
            )
        )

    return User.objects.none()


def get_allowed_message_recipients(user):
    gym_id = single_active_gym_id(user, [user.role])
    return _get_allowed_message_recipients(user).filter(is_active=True,
        gym_memberships__gym_id=gym_id, gym_memberships__is_active=True,
        role=F('gym_memberships__role')).distinct()


def users_may_message(sender, recipient):
    if sender.id == recipient.id:
        return False

    return get_allowed_message_recipients(
        sender
    ).filter(
        id=recipient.id
    ).exists()


def find_existing_direct_conversation(
    user_one,
    user_two,
    related_athlete=None
):
    conversations = Conversation.objects.filter(
        participants=user_one,
        gym_id=single_active_gym_id(user_one, [user_one.role]),
    ).exclude(gym__isnull=True).filter(
        participants=user_two
    ).distinct()

    for conversation in conversations:
        participant_ids = set(
            conversation.participants.values_list(
                'id',
                flat=True
            )
        )

        if participant_ids != {
            user_one.id,
            user_two.id,
        }:
            continue

        if related_athlete:
            if (
                conversation.related_athlete_id
                != related_athlete.id
            ):
                continue

        return conversation

    return None


@transaction.atomic
def create_or_get_conversation(
    *,
    creator,
    recipient,
    subject='',
    related_athlete=None,
    observer=None
):
    if not users_may_message(
        creator,
        recipient
    ):
        raise PermissionError(
            'You are not allowed to message this user.'
        )

    from .safeguarding import supervised_pair
    athlete = supervised_pair(creator, recipient, observer)
    if athlete is not None:
        if related_athlete is not None and related_athlete.pk != athlete.pk:
            raise PermissionError('Choose the athlete participating in this conversation.')
        related_athlete = athlete
    if related_athlete is not None:
        gym_id = single_active_gym_id(creator, [creator.role])
        if not GymMembership.objects.filter(user=related_athlete, role='athlete', gym_id=gym_id, is_active=True).exists():
            raise PermissionError('You cannot attach an athlete from another gym.')
        for person in (creator, recipient):
            if person.role == 'parent' and not ParentAthleteLink.objects.filter(parent=person, athlete=related_athlete, approved=True).exists():
                raise PermissionError('This parent does not have an approved connection to that athlete.')
    conversation = None
    if athlete is not None:
        for candidate in Conversation.objects.filter(gym_id=single_active_gym_id(creator, [creator.role]),
                related_athlete=athlete, requires_supervision=True, supervision_observer=observer,
                participants=creator).filter(participants=recipient).distinct():
            if set(candidate.participants.values_list('pk', flat=True)) == {creator.pk, recipient.pk, observer.pk}:
                conversation = candidate
                break
    else:
        conversation = find_existing_direct_conversation(creator, recipient, related_athlete=related_athlete)

    if conversation:
        if subject and not conversation.subject:
            conversation.subject = subject
            conversation.save(
                update_fields=[
                    'subject'
                ]
            )

        return conversation

    conversation = Conversation.objects.create(
        gym_id=single_active_gym_id(creator, [creator.role]),
        created_by=creator,
        subject=subject,
        related_athlete=related_athlete, requires_supervision=athlete is not None,
        supervision_observer=observer,
    )

    ConversationParticipant.objects.bulk_create([
        ConversationParticipant(
            conversation=conversation,
            user=creator
        ),
        ConversationParticipant(
            conversation=conversation,
            user=recipient
        ),
    ])

    if observer is not None:
        ConversationParticipant.objects.create(conversation=conversation, user=observer)

    return conversation


@transaction.atomic
def send_message(
    *,
    conversation,
    sender,
    body
):
    if conversation.gym_id is None or conversation.gym_id != single_active_gym_id(sender, [sender.role]):
        raise PermissionError('This conversation is outside your current gym.')
    if not conversation.participants.filter(
        id=sender.id
    ).exists():
        raise PermissionError(
            'You are not a participant in this conversation.'
        )

    from .safeguarding import can_view_conversation, supervision_error
    if not can_view_conversation(sender, conversation):
        raise PermissionError('This conversation is no longer available to your account.')
    error = supervision_error(conversation)
    if error:
        raise PermissionError(error)
    for participant_user in conversation.participants.all():
        if not can_view_conversation(participant_user, conversation):
            raise PermissionError('A participant no longer has access. Start a new conversation with the current participants.')

    cleaned_body = body.strip()

    if len(cleaned_body) > 10000:
        raise ValueError("Keep messages to 10,000 characters or fewer.")

    if not cleaned_body:
        raise ValueError(
            'Message cannot be empty.'
        )

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=cleaned_body
    )

    conversation.save(
        update_fields=[
            'updated_at'
        ]
    )

    participant = ConversationParticipant.objects.filter(
        conversation=conversation,
        user=sender
    ).first()

    if participant:
        participant.mark_read()

    recipients = conversation.participants.exclude(
        id=sender.id
    )

    message_link = reverse(
        'conversation_detail',
        args=[conversation.id]
    )

    sender_name = get_display_name(sender)

    for recipient in recipients:
        create_notification(
            recipient=recipient,
            sender=sender,
            title=f'New message from {sender_name}',
            message=cleaned_body[:140],
            notification_type=Notification.TYPE_MESSAGE,
            link=message_link
        )

    return message
