from .models import (
    ConversationParticipant,
    Notification,
)


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            'global_unread_notification_count': 0,
            'global_recent_notifications': [],
            'global_unread_message_count': 0,
        }

    notifications = (
        Notification.objects
        .filter(recipient=request.user)
        .select_related('sender')
        .order_by('-created_at')
    )

    participations = (
        ConversationParticipant.objects
        .filter(
            user=request.user,
            is_archived=False
        )
        .select_related('conversation')
    )

    unread_message_count = sum(
        participation.unread_count()
        for participation in participations
    )

    return {
        'global_unread_notification_count': (
            notifications
            .filter(is_read=False)
            .count()
        ),

        'global_recent_notifications': (
            notifications[:5]
        ),

        'global_unread_message_count': (
            unread_message_count
        ),
    }