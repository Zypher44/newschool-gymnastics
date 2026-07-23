from .models import Notification


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            'global_notifications': [],
            'global_unread_notification_count': 0,
        }

    unread_notifications = (
        Notification.objects
        .filter(
            recipient=request.user,
            is_read=False
        )
        .order_by('-created_at')
    )

    return {
        'global_notifications': unread_notifications[:5],
        'global_unread_notification_count': (
            unread_notifications.count()
        ),
    }