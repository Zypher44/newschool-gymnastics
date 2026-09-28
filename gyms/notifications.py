"""Notifications for membership and family requests inside one gym."""

from communications.models import Notification

from .models import GymMembership


def notify_gym_directors(gym, sender, title, message, link):
    director_ids = GymMembership.objects.filter(
        gym=gym, role='director', is_active=True,
    ).values_list('user_id', flat=True)
    Notification.objects.bulk_create([
        Notification(recipient_id=director_id, sender=sender,
                     notification_type=Notification.TYPE_SYSTEM,
                     title=title, message=message, link=link)
        for director_id in set(director_ids)
    ])
