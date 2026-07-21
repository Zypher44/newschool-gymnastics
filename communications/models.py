from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Notification(models.Model):
    TYPE_GENERAL = 'general'
    TYPE_WELLNESS = 'wellness'
    TYPE_TESTING = 'testing'
    TYPE_VIDEO = 'video'
    TYPE_EVENT = 'event'
    TYPE_ATTENDANCE = 'attendance'
    TYPE_ACHIEVEMENT = 'achievement'
    TYPE_MESSAGE = 'message'
    TYPE_SYSTEM = 'system'

    TYPE_CHOICES = [
        (TYPE_GENERAL, 'General'),
        (TYPE_WELLNESS, 'Wellness'),
        (TYPE_TESTING, 'Testing'),
        (TYPE_VIDEO, 'Video'),
        (TYPE_EVENT, 'Event'),
        (TYPE_ATTENDANCE, 'Attendance'),
        (TYPE_ACHIEVEMENT, 'Achievement'),
        (TYPE_MESSAGE, 'Message'),
        (TYPE_SYSTEM, 'System'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        null=True,
        blank=True
    )

    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_GENERAL
    )

    title = models.CharField(max_length=150)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

        indexes = [
            models.Index(
                fields=[
                    'recipient',
                    'is_read',
                    '-created_at',
                ]
            ),
        ]

    def __str__(self):
        return f'{self.recipient.username}: {self.title}'

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()

            self.save(
                update_fields=[
                    'is_read',
                    'read_at',
                ]
            )

    def get_icon(self):
        icons = {
            self.TYPE_GENERAL: '🔔',
            self.TYPE_WELLNESS: '💚',
            self.TYPE_TESTING: '📊',
            self.TYPE_VIDEO: '🎥',
            self.TYPE_EVENT: '📅',
            self.TYPE_ATTENDANCE: '✅',
            self.TYPE_ACHIEVEMENT: '🏆',
            self.TYPE_MESSAGE: '💬',
            self.TYPE_SYSTEM: '⚙️',
        }

        return icons.get(
            self.notification_type,
            '🔔'
        )

    def get_destination(self):
        if self.link:
            return self.link

        return reverse('notification_list')


class Conversation(models.Model):
    subject = models.CharField(
        max_length=180,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_conversations',
        null=True,
        blank=True
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='communication_conversations'
    )

    related_athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='related_communications',
        null=True,
        blank=True,
        limit_choices_to={
            'role': 'athlete'
        }
    )

    is_archived = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            '-updated_at'
        ]

    def __str__(self):
        if self.subject:
            return self.subject

        return f'Conversation {self.pk}'

    def get_absolute_url(self):
        return reverse(
            'conversation_detail',
            args=[self.pk]
        )

    def other_participants(self, user):
        return self.participants.exclude(
            id=user.id
        )

    def latest_message(self):
        return self.messages.order_by(
            '-created_at'
        ).first()


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participant_records'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_participations'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    last_read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_archived = models.BooleanField(
        default=False
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'conversation',
                    'user',
                ],
                name='unique_conversation_participant'
            ),
        ]

    def __str__(self):
        return (
            f'{self.user.username} in '
            f'{self.conversation}'
        )

    def mark_read(self):
        self.last_read_at = timezone.now()

        self.save(
            update_fields=[
                'last_read_at'
            ]
        )

    def unread_count(self):
        messages = self.conversation.messages.exclude(
            sender=self.user
        )

        if self.last_read_at:
            messages = messages.filter(
                created_at__gt=self.last_read_at
            )

        return messages.count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='communication_messages',
        null=True
    )

    body = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    edited_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_system_message = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = [
            'created_at'
        ]

        indexes = [
            models.Index(
                fields=[
                    'conversation',
                    'created_at',
                ]
            ),
        ]

    def __str__(self):
        return (
            f'Message from '
            f'{self.sender or "System"}'
        )