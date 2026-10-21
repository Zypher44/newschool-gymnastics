from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from .models import CommunicationPreference, QueuedParentReport, ParentReportDigest
from practice_focus.email_delivery import recipients_for, draft_problem, valid_address
from practice_focus.email_provider import email_configuration, submit_email, EmailDeliveryError
from practice_focus.engagement_access import coach_roster


def eligible_rows(parent):
    result = []
    for row in QueuedParentReport.objects.filter(parent=parent, delivered_at__isnull=True).filter(Q(batch__isnull=True) | Q(batch__status__in=['pending', 'failed', 'sending'])).select_related('draft__coach', 'draft__weekly_summary'):
        draft = row.draft
        try:
            gym_id, roster = coach_roster(draft.coach)
            valid = gym_id == draft.gym_id and not draft_problem(draft, draft.coach, gym_id, roster)
        except Exception:
            valid = False
        if valid and any(p.pk == parent.pk for p in recipients_for(draft, 'parents')):
            result.append(row)
    return result


def deliver_digest(parent_id):
    problem = email_configuration()
    if problem: return problem
    with transaction.atomic():
        preference = CommunicationPreference.objects.select_for_update().select_related('user').get(user_id=parent_id)
        parent = preference.user
        if not parent.is_active or parent.role != 'parent' or not preference.email_reports: return ''
        if preference.report_frequency != 'weekly': return ''
        if preference.last_digest_at and timezone.now() - preference.last_digest_at < timedelta(days=7): return ''
        if not valid_address(parent.email.strip()): return 'Parent has no valid email address.'
        rows = eligible_rows(parent)
        if not rows: return ''
        digest = ParentReportDigest.objects.filter(parent=parent, status__in=['pending', 'failed', 'sending']).order_by('created_at').first()
        if digest:
            ids = set(digest.queuedparentreport_set.values_list('pk', flat=True))
            current_ids = {row.pk for row in rows}
            if not ids.issubset(current_ids) or digest.payload.get('to') != [parent.email.strip()] or timezone.now()-digest.created_at > timedelta(hours=23):
                digest.status = 'blocked'; digest.last_error = 'Saved email changed or confirmation expired. Review delivery before resending.'; digest.save()
                return digest.last_error
        else:
            from django.urls import reverse
            # Links reveal report content only after a fresh parent login and access check.
            items = [(row.draft.snapshot.get('athlete_name', ''), row.draft.snapshot.get('title', 'Progress report'),
                      settings.REPORT_EMAIL_APP_URL.rstrip('/') + reverse('practice_focus:family_progress') + f'?athlete={row.draft.athlete_id}') for row in rows]
            html = format_html('<h1>Your weekly progress updates</h1><ul>{}</ul>', format_html_join('', '<li>{}: <a href="{}">{}</a></li>', ((name, url, title) for name,title,url in items)))
            digest = ParentReportDigest.objects.create(parent=parent, payload={'from': settings.REPORT_EMAIL_FROM,
                'to': [parent.email.strip()], 'subject': 'Your weekly gymnastics progress updates', 'html': str(html),
                'text': 'Your weekly progress updates\n' + '\n'.join(f'{name}: {title} {url}' for name,title,url in items)})
            QueuedParentReport.objects.filter(pk__in=[row.pk for row in rows]).update(batch=digest)
        if digest.status == 'sending': return 'Delivery already in progress; review before retrying.'
        digest.status = 'sending'; digest.save(update_fields=['status'])
    try:
        submit_email(digest.payload, digest.token)
    except EmailDeliveryError as error:
        digest.status = 'failed'; digest.last_error = str(error); digest.save(update_fields=['status','last_error'])
        return str(error)
    with transaction.atomic():
        now = timezone.now()
        ParentReportDigest.objects.filter(pk=digest.pk).update(status='submitted', submitted_at=now, last_error='')
        QueuedParentReport.objects.filter(batch=digest).update(delivered_at=now)
        CommunicationPreference.objects.filter(user=parent).update(last_digest_at=now)
    return ''
