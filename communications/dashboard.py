from django.db.models import Max, Q

from accounts.models import User
from coaches.models import CoachAthleteAssignment
from parents_portal.models import ParentAthleteLink

from .models import (
    Conversation,
    ConversationParticipant,
)
from .services import (
    create_or_get_conversation,
    get_allowed_message_recipients,
    send_message,
)


def get_user_display_name(user):
    if not user:
        return ''

    full_name = user.get_full_name().strip()

    if full_name:
        return full_name

    return user.username


def get_recent_conversations(user, limit=3):
    """
    Return recent conversations formatted for dashboard cards.
    """

    participations = (
        ConversationParticipant.objects
        .filter(
            user=user,
            is_archived=False,
            conversation__is_archived=False
        )
        .select_related(
            'conversation',
            'conversation__related_athlete'
        )
        .prefetch_related(
            'conversation__participants',
            'conversation__messages__sender'
        )
        .annotate(
            latest_activity=Max(
                'conversation__messages__created_at'
            )
        )
        .order_by(
            '-latest_activity',
            '-conversation__updated_at'
        )[:limit]
    )

    rows = []

    for participation in participations:
        conversation = participation.conversation

        other_users = list(
            conversation.participants.exclude(
                id=user.id
            )
        )

        latest_message = conversation.latest_message()

        participant_names = [
            get_user_display_name(other_user)
            for other_user in other_users
        ]

        rows.append({
            'conversation': conversation,
            'participant_names': ', '.join(
                participant_names
            ),
            'latest_message': latest_message,
            'unread_count': participation.unread_count(),
            'related_athlete': (
                conversation.related_athlete
            ),
        })

    return rows


def get_coach_quick_message_options(coach):
    """
    Return athletes and linked parents available to a coach.
    """

    if coach.role == 'head_coach':
        athletes = User.objects.filter(
            role='athlete'
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )
    else:
        athlete_ids = (
            CoachAthleteAssignment.objects
            .filter(coach=coach)
            .values_list(
                'athlete_id',
                flat=True
            )
        )

        athletes = User.objects.filter(
            id__in=athlete_ids,
            role='athlete'
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )

    options = []

    for athlete in athletes:
        parent_ids = (
            ParentAthleteLink.objects
            .filter(athlete=athlete)
            .values_list(
                'parent_id',
                flat=True
            )
        )

        parents = User.objects.filter(
            id__in=parent_ids,
            role='parent'
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )

        options.append({
            'athlete': athlete,
            'athlete_name': get_user_display_name(
                athlete
            ),
            'parents': parents,
        })

    return options


def get_athlete_quick_message_options(athlete):
    """
    Return coaches assigned to an athlete.
    """

    coach_ids = (
        CoachAthleteAssignment.objects
        .filter(athlete=athlete)
        .values_list(
            'coach_id',
            flat=True
        )
    )

    return User.objects.filter(
        id__in=coach_ids,
        role__in=[
            'coach',
            'head_coach',
        ]
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )


def get_parent_quick_message_options(parent):
    """
    Return each linked athlete and their assigned coaches.
    """

    links = (
        ParentAthleteLink.objects
        .filter(parent=parent)
        .select_related('athlete')
    )

    options = []

    for link in links:
        athlete = link.athlete

        coach_ids = (
            CoachAthleteAssignment.objects
            .filter(athlete=athlete)
            .values_list(
                'coach_id',
                flat=True
            )
        )

        coaches = User.objects.filter(
            id__in=coach_ids,
            role__in=[
                'coach',
                'head_coach',
            ]
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )

        options.append({
            'athlete': athlete,
            'athlete_name': get_user_display_name(
                athlete
            ),
            'coaches': coaches,
        })

    return options


def get_dashboard_communication_data(user):
    """
    Return role-specific data used by the shared dashboard card.
    """

    data = {
        'recent_conversations': (
            get_recent_conversations(user)
        ),
        'coach_options': [],
        'athlete_coaches': [],
        'parent_options': [],
    }

    if user.role in [
        'coach',
        'head_coach',
    ]:
        data['coach_options'] = (
            get_coach_quick_message_options(user)
        )

    elif user.role == 'athlete':
        data['athlete_coaches'] = (
            get_athlete_quick_message_options(user)
        )

    elif user.role == 'parent':
        data['parent_options'] = (
            get_parent_quick_message_options(user)
        )

    return data


def send_dashboard_message(
    *,
    sender,
    recipient,
    message_body,
    related_athlete=None,
    subject=''
):
    """
    Create or reuse a conversation and send one message.
    """

    conversation = create_or_get_conversation(
        creator=sender,
        recipient=recipient,
        subject=subject,
        related_athlete=related_athlete
    )

    send_message(
        conversation=conversation,
        sender=sender,
        body=message_body
    )

    return conversation