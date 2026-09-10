from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.dateparse import parse_date

from communications.models import Notification

from .models import TeamEvent


User = get_user_model()


@receiver(
    post_save,
    sender=TeamEvent,
)
def notify_parents_about_new_event(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Automatically notify active parents
    when a new TeamEvent is created.
    """

    if not created:
        return


    event_date = instance.event_date

    if isinstance(
        event_date,
        str,
    ):
        event_date = parse_date(
            event_date
        )


    if event_date:
        formatted_date = event_date.strftime(
            '%B %d, %Y'
        )
    else:
        formatted_date = (
            'an upcoming date'
        )


    parents = (
        User.objects
        .filter(
            role='parent',
            is_active=True,
        )
    )


    notifications = []


    for parent in parents:

        notifications.append(
            Notification(
                recipient=parent,

                notification_type=(
                    Notification.TYPE_EVENT
                ),

                title=(
                    f'New Event: '
                    f'{instance.title}'
                ),

                message=(
                    f'{instance.title} has been added '
                    f'for {formatted_date}.'
                ),

                link=(
                    '/parents/events/'
                ),
            )
        )


    if notifications:

        Notification.objects.bulk_create(
            notifications
        )