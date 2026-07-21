from django.db import transaction
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
    coach_ids = CoachAthleteAssignment.objects.filter(
        athlete=athlete
    ).values_list(
        'coach_id',
        flat=True
    )

    return User.objects.filter(
        id__in=coach_ids,
        role__in=[
            'coach',
            'head_coach',
        ]
    ).distinct()

def get_parents_for_athlete(athlete):
    parent_ids = ParentAthleteLink.objects.filter(
        athlete=athlete
    ).values_list(
        'parent_id',
        flat=True
    )

    return User.objects.filter(
        id__in=parent_ids,
        role='parent'
    ).distinct()

def get_athletes_for_coach(coach):
    if coach.role == 'head_coach':
        return User.objects.filter(
            role='athlete'
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
        role='athlete'
    ).order_by(
        'first_name',
        'username'
    )

def get_allowed_message_recipients(user):
    """
    Return users that the current user may message.
    """

    if user.role == 'head_coach':
        return User.objects.exclude(
            id=user.id
        ).filter(
            role__in=[
                'coach',
                'head_coach',
                'athlete',
                'parent',
            ]
        ).order_by(
            'role',
            'first_name',
            'username'
        )

    if user.role == 'coach':
        athletes = get_athletes_for_coach(user)

        athlete_ids = athletes.values_list(
            'id',
            flat=True
        )

        parent_ids = ParentAthleteLink.objects.filter(
            athlete_id__in=athlete_ids
        ).values_list(
            'parent_id',
            flat=True
        )

        return User.objects.filter(
            id__in=list(athlete_ids) + list(parent_ids)
        ).exclude(
            id=user.id
        ).distinct().order_by(
            'role',
            'first_name',
            'username'
        )

    if user.role == 'athlete':
        return get_coaches_for_athlete(user).exclude(
            id=user.id
        )

    if user.role == 'parent':
        linked_athlete_ids = ParentAthleteLink.objects.filter(
            parent=user
        ).values_list(
            'athlete_id',
            flat=True
        )

        coach_ids = CoachAthleteAssignment.objects.filter(
            athlete_id__in=linked_athlete_ids
        ).values_list(
            'coach_id',
            flat=True
        )

        return User.objects.filter(
            id__in=coach_ids,
            role__in=[
                'coach',
                'head_coach',
            ]
        ).distinct().order_by(
            'first_name',
            'username'
        )

    return User.objects.none()


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
        participants=user_one
    ).filter(
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
    related_athlete=None
):
    if not users_may_message(
        creator,
        recipient
    ):
        raise PermissionError(
            'You are not allowed to message this user.'
        )

    conversation = find_existing_direct_conversation(
        creator,
        recipient,
        related_athlete=related_athlete
    )

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
        created_by=creator,
        subject=subject,
        related_athlete=related_athlete
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

    return conversation


@transaction.atomic
def send_message(
    *,
    conversation,
    sender,
    body
):
    if not conversation.participants.filter(
        id=sender.id
    ).exists():
        raise PermissionError(
            'You are not a participant in this conversation.'
        )

    cleaned_body = body.strip()

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