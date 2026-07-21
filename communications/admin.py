from django.contrib import admin

from .models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'recipient',
        'notification_type',
        'is_read',
        'created_at',
    ]

    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
    ]

    search_fields = [
        'title',
        'message',
        'recipient__username',
    ]


class ConversationParticipantInline(
    admin.TabularInline
):
    model = ConversationParticipant
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'subject',
        'related_athlete',
        'created_by',
        'updated_at',
    ]

    search_fields = [
        'subject',
        'participants__username',
    ]

    inlines = [
        ConversationParticipantInline
    ]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'conversation',
        'sender',
        'created_at',
    ]

    search_fields = [
        'body',
        'sender__username',
    ]

    readonly_fields = [
        'created_at',
        'edited_at',
    ]