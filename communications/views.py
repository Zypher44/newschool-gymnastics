from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .forms import (
    MessageForm,
    NewConversationForm,
)
from .models import (
    Conversation,
    ConversationParticipant,
    Notification,
)
from .services import (
    create_or_get_conversation,
    send_message,
)


@login_required
def communication_inbox(request):
    participations = (
        ConversationParticipant.objects
        .filter(
            user=request.user,
            is_archived=False,
            conversation__is_archived=False
        )
        .select_related(
            'conversation',
            'conversation__related_athlete'
        )
        .prefetch_related(
            'conversation__participants',
            'conversation__messages',
        )
        .order_by(
            '-conversation__updated_at'
        )
    )

    conversation_rows = []

    for participation in participations:
        conversation = participation.conversation

        conversation_rows.append({
            'conversation': conversation,
            'other_participants': (
                conversation.other_participants(
                    request.user
                )
            ),
            'latest_message': (
                conversation.latest_message()
            ),
            'unread_count': (
                participation.unread_count()
            ),
        })

    total_unread_messages = sum(
        row['unread_count']
        for row in conversation_rows
    )

    return render(
        request,
        'communications/inbox.html',
        {
            'conversation_rows': conversation_rows,
            'total_unread_messages': (
                total_unread_messages
            ),
        }
    )


@login_required
def conversation_create(request):
    if request.method == 'POST':
        form = NewConversationForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            recipient = form.cleaned_data[
                'recipient'
            ]

            subject = form.cleaned_data[
                'subject'
            ]

            message_body = form.cleaned_data[
                'message'
            ]

            try:
                conversation = (
                    create_or_get_conversation(
                        creator=request.user,
                        recipient=recipient,
                        subject=subject
                    )
                )

                send_message(
                    conversation=conversation,
                    sender=request.user,
                    body=message_body
                )

                messages.success(
                    request,
                    'Your message was sent.'
                )

                return redirect(
                    'conversation_detail',
                    conversation_id=conversation.id
                )

            except PermissionError as error:
                form.add_error(
                    'recipient',
                    str(error)
                )

            except ValueError as error:
                form.add_error(
                    'message',
                    str(error)
                )

    else:
        form = NewConversationForm(
            user=request.user
        )

    return render(
        request,
        'communications/conversation_create.html',
        {
            'form': form,
        }
    )


@login_required
def conversation_detail(
    request,
    conversation_id
):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related(
            'participants',
            'messages__sender'
        ),
        id=conversation_id
    )

    participation = (
        ConversationParticipant.objects
        .filter(
            conversation=conversation,
            user=request.user
        )
        .first()
    )

    if not participation:
        raise Http404(
            'Conversation not found.'
        )

    participation.mark_read()

    Notification.objects.filter(
        recipient=request.user,
        notification_type=Notification.TYPE_MESSAGE,
        link=conversation.get_absolute_url(),
        is_read=False
    ).update(
        is_read=True
    )

    if request.method == 'POST':
        form = MessageForm(
            request.POST
        )

        if form.is_valid():
            try:
                send_message(
                    conversation=conversation,
                    sender=request.user,
                    body=form.cleaned_data[
                        'message'
                    ]
                )

                return redirect(
                    'conversation_detail',
                    conversation_id=conversation.id
                )

            except (
                PermissionError,
                ValueError
            ) as error:
                form.add_error(
                    'message',
                    str(error)
                )

    else:
        form = MessageForm()

    other_participants = (
        conversation.other_participants(
            request.user
        )
    )

    return render(
        request,
        'communications/conversation_detail.html',
        {
            'conversation': conversation,
            'other_participants': other_participants,
            'conversation_messages': (
                conversation.messages.select_related(
                    'sender'
                )
            ),
            'form': form,
        }
    )


@login_required
@require_POST
def conversation_archive(
    request,
    conversation_id
):
    participation = get_object_or_404(
        ConversationParticipant,
        conversation_id=conversation_id,
        user=request.user
    )

    participation.is_archived = True
    participation.save(
        update_fields=[
            'is_archived'
        ]
    )

    messages.success(
        request,
        'Conversation archived.'
    )

    return redirect(
        'communication_inbox'
    )


@login_required
def notification_list(request):
    notification_filter = request.GET.get(
        'filter',
        'all'
    )

    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related(
        'sender'
    )

    if notification_filter == 'unread':
        notifications = notifications.filter(
            is_read=False
        )

    elif notification_filter == 'read':
        notifications = notifications.filter(
            is_read=True
        )

    elif notification_filter != 'all':
        notification_filter = 'all'

    paginator = Paginator(
        notifications,
        20
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    total_count = Notification.objects.filter(
        recipient=request.user
    ).count()

    return render(
        request,
        'communications/notification_list.html',
        {
            'page_obj': page_obj,
            'notification_filter': (
                notification_filter
            ),
            'unread_count': unread_count,
            'total_count': total_count,
        }
    )


@login_required
def notification_open(
    request,
    notification_id
):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.mark_as_read()

    return redirect(
        notification.get_destination()
    )


@login_required
@require_POST
def notification_mark_read(
    request,
    notification_id
):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.mark_as_read()

    return redirect(
        request.POST.get(
            'next',
            'notification_list'
        )
    )


@login_required
@require_POST
def notification_mark_unread(
    request,
    notification_id
):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.is_read = False
    notification.read_at = None

    notification.save(
        update_fields=[
            'is_read',
            'read_at',
        ]
    )

    return redirect(
        request.POST.get(
            'next',
            'notification_list'
        )
    )


@login_required
@require_POST
def notification_mark_all_read(request):
    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )

    for notification in unread_notifications:
        notification.mark_as_read()

    return redirect(
        'notification_list'
    )


@login_required
@require_POST
def notification_delete(
    request,
    notification_id
):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.delete()

    return redirect(
        request.POST.get(
            'next',
            'notification_list'
        )
    )


@login_required
@require_POST
def notification_clear_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()

    return redirect(
        'notification_list'
    )