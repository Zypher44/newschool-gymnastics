from .models import (
    ConversationParticipant,
    Notification,
)


def communication_context(
    request,
):
    if not request.user.is_authenticated:

        return {
            'global_unread_notification_count': 0,
            'global_recent_notifications': [],
            'global_unread_message_count': 0,
        }


    # ========================================================
    # NOTIFICATIONS
    # ========================================================

    notifications = (
        Notification.objects
        .filter(
            recipient=request.user,
        )
        .select_related(
            'sender',
        )
        .order_by(
            '-created_at',
        )
    )


    global_unread_notification_count = (
        notifications
        .filter(
            is_read=False,
        )
        .count()
    )


    global_recent_notifications = list(
        notifications[:8]
    )


    # ========================================================
    # MESSAGES
    # ========================================================

    participations = (
        ConversationParticipant.objects
        .filter(
            user=request.user,
            is_archived=False,
            conversation__is_archived=False,
        )
        .select_related(
            'conversation',
        )
    )


    global_unread_message_count = sum(
        participation.unread_count()
        for participation
        in participations
    )


    # ========================================================
    # GLOBAL CONTEXT
    # ========================================================

    return {
        'global_unread_notification_count': (
            global_unread_notification_count
        ),

        'global_recent_notifications': (
            global_recent_notifications
        ),

        'global_unread_message_count': (
            global_unread_message_count
        ),
    }