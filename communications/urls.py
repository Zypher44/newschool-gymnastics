from django.urls import path

from . import views


urlpatterns = [
    path(
        'messages/',
        views.communication_inbox,
        name='communication_inbox'
    ),

    path(
        'messages/new/',
        views.conversation_create,
        name='conversation_create'
    ),

    path(
        'messages/<int:conversation_id>/',
        views.conversation_detail,
        name='conversation_detail'
    ),

    path(
        'messages/<int:conversation_id>/archive/',
        views.conversation_archive,
        name='conversation_archive'
    ),

    path(
        'notifications/',
        views.notification_list,
        name='notification_list'
    ),

    path(
        'notifications/<int:notification_id>/open/',
        views.notification_open,
        name='notification_open'
    ),

    path(
        'notifications/<int:notification_id>/read/',
        views.notification_mark_read,
        name='notification_mark_read'
    ),

    path(
        'notifications/<int:notification_id>/unread/',
        views.notification_mark_unread,
        name='notification_mark_unread'
    ),

    path(
        'notifications/<int:notification_id>/delete/',
        views.notification_delete,
        name='notification_delete'
    ),

    path(
        'notifications/mark-all-read/',
        views.notification_mark_all_read,
        name='notification_mark_all_read'
    ),

    path(
        'notifications/clear-read/',
        views.notification_clear_read,
        name='notification_clear_read'
    ),
]