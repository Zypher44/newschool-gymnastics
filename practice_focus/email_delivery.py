from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from gyms.tenant import single_active_gym_id
from parents_portal.models import ParentAthleteLink
from .models import EmailReportDraft, ReportEmailDelivery
from .email_provider import EmailDeliveryError, email_configuration, submit_email
from .report_preferences import show_group_averages


def valid_address(address):
    try:
        validate_email(address)
        return bool(address) and '\n' not in address and '\r' not in address
    except ValidationError:
        return False


def recipients_for(draft, mode):
    if mode == 'self':
        return [draft.coach] if valid_address(draft.coach.email.strip()) else []
    if mode != 'parents' or not draft.athlete_id:
        return []
    links = ParentAthleteLink.objects.filter(athlete_id=draft.athlete_id, approved=True,
        parent__is_active=True, parent__role='parent', parent__gym_memberships__gym_id=draft.gym_id,
        parent__gym_memberships__role='parent', parent__gym_memberships__is_active=True).select_related('parent').distinct()
    result, seen = [], set()
    for link in links:
        parent = link.parent
        address = parent.email.strip()
        if single_active_gym_id(parent, ['parent']) != draft.gym_id or not valid_address(address) or address.lower() in seen:
            continue
        seen.add(address.lower()); result.append(parent)
    return result


def draft_problem(draft, coach, gym_id, roster):
    if draft.coach_id != coach.pk or draft.gym_id != gym_id:
        return 'This report is outside your coaching account.'
    ids = set(draft.snapshot.get('athlete_ids', []))
    if ids - set(roster.values_list('pk', flat=True)):
        return 'Your athlete access changed. Build a new report preview.'
    if draft.weekly_summary_id:
        summary = draft.weekly_summary
        if not summary.published_at or summary.published_at != draft.publication or summary.coach_id != coach.pk:
            return 'The weekly report changed or was withdrawn. Publish it and build a new email preview.'
    if draft.snapshot.get('include_group') and not show_group_averages(coach, gym_id):
        return 'Group averages are now hidden. Build a new preview before emailing.'
    return ''


def message_payload(draft, recipient):
    base_url = settings.REPORT_EMAIL_APP_URL.rstrip('/')
    if draft.weekly_summary_id:
        report_url = base_url + reverse('practice_focus:weekly_report_detail', args=[draft.weekly_summary_id])
    elif recipient.role == 'parent':
        report_url = base_url + reverse('practice_focus:family_progress') + f'?athlete={draft.athlete_id}'
    else:
        report_url = base_url + reverse('practice_focus:email_report_detail', args=[draft.pk])
    context = {'report': draft.snapshot, 'gym_name': draft.gym.name,
        'coach_name': draft.coach.get_full_name() or draft.coach.username, 'report_url': report_url}
    name = draft.snapshot.get('athlete_name', '')
    subject = f"{draft.gym.name} | {draft.snapshot['title']} | {name}"
    return {'from': settings.REPORT_EMAIL_FROM, 'to': [recipient.email.strip()],
        'subject': subject.replace('\r', ' ').replace('\n', ' ')[:250],
        'html': render_to_string('practice_focus/email_message.html', context),
        'text': render_to_string('practice_focus/email_message.txt', context)}


def send_report(draft, mode, gym_id, roster):
    """Explicit coach POST, bounded to two deliveries per request; retries keep each message/token."""
    issue = email_configuration() or draft_problem(draft, draft.coach, gym_id, roster)
    if issue:
        return {'submitted': 0, 'remaining': 0, 'error': issue}
    recipients = recipients_for(draft, mode)
    if not recipients:
        return {'submitted': 0, 'remaining': 0, 'error': 'No eligible recipient has a valid email address. Update the linked parent or your coach account.'}
    submitted, attempts, remaining, errors = 0, 0, 0, []
    for recipient in recipients:
        with transaction.atomic():
            # Lock one preview to coordinate double clicks, tabs, and retry requests.
            current = EmailReportDraft.objects.select_for_update().select_related('weekly_summary', 'coach').get(pk=draft.pk)
            problem = draft_problem(current, current.coach, gym_id, roster)
            if problem:
                errors.append(problem); break
            fresh = next((p for p in recipients_for(current, mode) if p.pk == recipient.pk), None)
            if fresh is None:
                continue
            recipient = fresh
            address = recipient.email.strip()
            delivery, _ = ReportEmailDelivery.objects.get_or_create(draft=current, email=address.lower(), defaults={'recipient': recipient})
            if delivery.status == 'submitted':
                continue
            now = timezone.now()
            if delivery.status == 'sending' and delivery.last_attempt and now - delivery.last_attempt < timedelta(minutes=2):
                remaining += 1; continue
            if delivery.first_attempt and now - delivery.first_attempt > timedelta(hours=23) and delivery.may_have_sent:
                delivery.status = 'blocked'
                delivery.last_error = 'Confirmation expired. Check the email provider before creating a new preview.'
                delivery.save(update_fields=['status', 'last_error'])
            if delivery.status == 'blocked':
                errors.append(delivery.last_error); continue
            if attempts >= 2:
                remaining += 1; continue
            new_payload = message_payload(draft, recipient)
            if delivery.payload and delivery.payload != new_payload:
                delivery.status = 'blocked'; delivery.last_error = 'The sender, recipient, or preview changed. Build a fresh preview.'
                delivery.save(update_fields=['status', 'last_error'])
                errors.append(delivery.last_error); continue
            # A definitely refused request may be tried after the provider's retention window.
            if delivery.first_attempt and now - delivery.first_attempt > timedelta(hours=23):
                from uuid import uuid4
                delivery.token = uuid4(); delivery.first_attempt = now
            prior_uncertainty = delivery.may_have_sent
            delivery.payload = new_payload; delivery.status = 'sending'; delivery.last_error = ''; delivery.may_have_sent = True
            delivery.first_attempt = delivery.first_attempt or now; delivery.last_attempt = now; delivery.save()
        attempts += 1
        try:
            provider_id = submit_email(delivery.payload, delivery.token)
        except EmailDeliveryError as error:
            ReportEmailDelivery.objects.filter(pk=delivery.pk).update(
                status='unconfirmed' if error.uncertain or prior_uncertainty else 'failed',
                may_have_sent=error.uncertain or prior_uncertainty, last_error=str(error)[:300])
            errors.append(str(error))
        else:
            ReportEmailDelivery.objects.filter(pk=delivery.pk).update(status='submitted', provider_id=provider_id, submitted_at=timezone.now(), last_error='')
            submitted += 1
    return {'submitted': submitted, 'remaining': remaining, 'error': ' '.join(dict.fromkeys(errors))}
