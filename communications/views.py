from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.urls import reverse
from gyms.tenant import single_active_gym_id
from coaches.audiences import audience_members, selectable_groups
from .dashboard import send_dashboard_message
from accounts.models import User
from .services import get_allowed_message_recipients
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme
from .safeguarding import can_view_conversation, supervision_error, visible_conversation_ids, visible_notifications, active_members, OBSERVER_ROLES

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
def gym_announcement(request):
    """Send individual private messages to members of a gym audience."""
    if request.user.role not in ('director', 'coach', 'head_coach') or not single_active_gym_id(request.user, [request.user.role]):
        raise Http404

    groups = selectable_groups(request.user)
    observer_options = active_members(single_active_gym_id(request.user, [request.user.role])).filter(role__in=OBSERVER_ROLES).exclude(pk=request.user.pk)
    error = None
    if request.method == 'POST':
        audience = request.POST.get('audience', '')
        group_id = request.POST.get('training_group', '')
        group = groups.filter(pk=group_id).first() if group_id.isdigit() else None
        body = request.POST.get('message', '').strip()
        subject = request.POST.get('subject', '').strip()[:180]
        if audience not in ('all', 'coaches', 'parents', 'group'):
            error = 'Choose an audience.'
        elif audience == 'group' and group is None:
            error = 'Choose a training group assigned to you.'
        elif not body:
            error = 'Enter a message.'
        else:
            allowed = get_allowed_message_recipients(request.user)
            recipients = list(audience_members(request.user, audience, group).filter(pk__in=allowed.values('pk')))
            if not recipients:
                error = 'No active gym members match that audience.'
            else:
                observer_id = request.POST.get('observer', '')
                observer = observer_options.filter(pk=observer_id).first() if observer_id.isdigit() else None
                if any(person.role == 'athlete' for person in recipients) and observer is None:
                    error = 'Choose a second gym staff member to observe athlete conversations before sending.'
                else:
                    try:
                        with transaction.atomic():
                            for recipient in recipients:
                                conversation = create_or_get_conversation(creator=request.user,
                                    recipient=recipient, subject=subject,
                                    observer=observer if recipient.role == 'athlete' else None)
                                send_message(conversation=conversation, sender=request.user, body=body)
                    except (PermissionError, ValueError) as exc:
                        error = str(exc)
                if error:
                    return render(request, 'communications/gym_announcement.html', {
                        'groups': groups, 'error': error, 'observer_options': observer_options,
                    })
                messages.success(request, f'Message sent to {len(recipients)} gym members.')
                return redirect('communication_inbox')

    return render(request, 'communications/gym_announcement.html', {
        'groups': groups, 'error': error, 'observer_options': observer_options,
    })

@login_required
@require_POST
def dashboard_message_send(request):
    recipient_id = request.POST.get(
        'recipient'
    )

    message_body = request.POST.get(
        'message',
        ''
    ).strip()

    related_athlete_id = request.POST.get(
        'related_athlete'
    )

    next_url = request.POST.get(
        'next'
    )

    if next_url and not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = None

    if not recipient_id:
        messages.error(
            request,
            'Please choose a recipient.'
        )

        return redirect(
            next_url or 'communication_inbox'
        )

    if not message_body:
        messages.error(
            request,
            'Please enter a message.'
        )

        return redirect(
            next_url or 'communication_inbox'
        )

    if not recipient_id.isdigit():
        raise Http404('Choose a valid recipient.')

    allowed_recipients = (
        get_allowed_message_recipients(
            request.user
        )
    )

    recipient = allowed_recipients.filter(
        id=recipient_id
    ).first()

    if recipient is None:
        messages.error(
            request,
            'You are not allowed to message that user.'
        )

        return redirect(
            next_url or 'communication_inbox'
        )

    draft_form = NewConversationForm(request.POST, user=request.user)
    if not draft_form.is_valid():
        return render(request, 'communications/conversation_create.html', {'form': draft_form})

    related_athlete = None

    if related_athlete_id and not related_athlete_id.isdigit():
        raise Http404('Choose a valid athlete.')
    if related_athlete_id:
        related_athlete = User.objects.filter(
            id=related_athlete_id,
            role='athlete'
        ).first()

    try:
        conversation = send_dashboard_message(
            sender=request.user,
            recipient=recipient,
            message_body=message_body,
            related_athlete=related_athlete,
            observer=draft_form.cleaned_data.get('observer'),
        )

    except (
        PermissionError,
        ValueError
    ) as error:
        messages.error(
            request,
            str(error)
        )

        return redirect(
            next_url or 'communication_inbox'
        )

    messages.success(
        request,
        'Message sent successfully.'
    )

    return redirect(
        next_url or reverse(
            'conversation_detail',
            args=[conversation.id]
        )
    )

@login_required
@never_cache
def communication_inbox(request):
    participations = (
        ConversationParticipant.objects
        .filter(
            user=request.user,
            conversation_id__in=visible_conversation_ids(request.user),
            conversation__gym_id=single_active_gym_id(request.user, [request.user.role]),
            conversation__gym__isnull=False,
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
@never_cache
@require_http_methods(['GET', 'POST'])
@transaction.atomic
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
                with transaction.atomic():
                    conversation = (
                        create_or_get_conversation(
                            creator=request.user,
                            recipient=recipient,
                            subject=subject, observer=form.cleaned_data.get('observer'),
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
        initial = {'recipient': request.GET.get('recipient', ''), 'subject': {'question': 'Question about my practice goal', 'win': 'A learning win to share', 'goal': 'My next practice goal'}.get(request.GET.get('topic'), '')}
        form = NewConversationForm(user=request.user, initial=initial)

    return render(
        request,
        'communications/conversation_create.html',
        {
            'form': form,
        }
    )


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def conversation_detail(
    request,
    conversation_id
):
    conversation = get_object_or_404(
        Conversation.objects.filter(gym_id=single_active_gym_id(request.user, [request.user.role]))
        .exclude(gym__isnull=True).prefetch_related(
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

    if not participation or not can_view_conversation(request.user, conversation):
        raise Http404(
            'Conversation not found.'
        )

    conversation_guard = supervision_error(conversation)
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
            'form': form, 'conversation_guard': conversation_guard,
        }
    )


@login_required
@require_POST
def conversation_archive(
    request,
    conversation_id
):
    participation = get_object_or_404(
        ConversationParticipant.objects.filter(
            conversation__gym_id=single_active_gym_id(request.user, [request.user.role]),
            conversation__gym__isnull=False),
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
@never_cache
def notification_list(
    request,
):
    # ========================================================
    # FILTER
    # ========================================================

    notification_filter = (
        request.GET.get(
            'filter',
            'all',
        )
        .strip()
        .lower()
    )

    allowed_filters = {
        'all',
        'unread',
        'read',
    }

    if (
        notification_filter
        not in allowed_filters
    ):
        notification_filter = (
            'all'
        )


    # ========================================================
    # ALL USER NOTIFICATIONS
    # ========================================================

    all_notifications = (
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


    all_notifications = visible_notifications(request.user, all_notifications)

    total_count = (
        all_notifications.count()
    )


    unread_count = (
        all_notifications
        .filter(
            is_read=False,
        )
        .count()
    )


    # ========================================================
    # APPLY FILTER
    # ========================================================

    if (
        notification_filter
        == 'unread'
    ):

        notifications = (
            all_notifications
            .filter(
                is_read=False,
            )
        )


    elif (
        notification_filter
        == 'read'
    ):

        notifications = (
            all_notifications
            .filter(
                is_read=True,
            )
        )


    else:

        notifications = (
            all_notifications
        )


    # ========================================================
    # PAGINATION
    # ========================================================

    paginator = Paginator(
        notifications,
        15,
    )


    page_number = (
        request.GET.get(
            'page'
        )
    )


    page_obj = (
        paginator.get_page(
            page_number
        )
    )


    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        'notifications': (
            notifications
        ),

        'page_obj': (
            page_obj
        ),

        'notification_filter': (
            notification_filter
        ),

        'unread_count': (
            unread_count
        ),

        'total_count': (
            total_count
        ),
    }


    return render(
        request,
        'communications/notification_list.html',
        context,
    )
@login_required
def notification_open(
    request,
    notification_id
):
    notification = get_object_or_404(
        visible_notifications(request.user, Notification.objects.filter(recipient=request.user)),
        id=notification_id,
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
