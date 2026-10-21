import hashlib
import json
from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from gyms.models import Gym, GymMembership
from .models import EmailReportDraft, WeeklyProgressSummary
from .engagement_access import coach_roster
from .email_delivery import draft_problem, recipients_for, send_report
from .email_provider import email_configuration
from .email_snapshots import REPORT_TITLES, build_snapshot, snapshot_for_week


def email_roster(coach):
    gym_id, people = coach_roster(coach)
    # Legacy attendance/wellness records have no gym FK: don't mix multi-gym records in emails.
    ambiguous = GymMembership.objects.filter(role='athlete', is_active=True, gym__is_active=True).values('user_id').annotate(gyms=Count('gym_id', distinct=True)).filter(gyms__gt=1).values('user_id')
    return gym_id, people.exclude(pk__in=ambiguous)


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def email_report_preview(request, kind):
    if kind not in REPORT_TITLES:
        return HttpResponseBadRequest('Choose a valid report.')
    gym_id, athletes = email_roster(request.user)
    values = request.POST if request.method == 'POST' else request.GET
    weekly = None
    try:
        selected = values.get('athlete')
        athlete = get_object_or_404(athletes, pk=int(selected)) if selected else None
        if kind == 'progress' and athlete is None:
            athlete = athletes.first()
        today = timezone.localdate()
        start = date.fromisoformat(values.get('start_date') or (today if kind == 'readiness' else today - timedelta(days=90)).isoformat())
        end = date.fromisoformat(values.get('end_date') or today.isoformat())
        if start > end:
            start, end = end, start
        if end > today:
            raise ValueError()
        if kind == 'weekly':
            weekly = get_object_or_404(WeeklyProgressSummary.objects.select_related('athlete', 'coach').filter(
                gym_id=gym_id, coach=request.user, athlete__in=athletes, published_at__isnull=False), pk=int(values.get('summary', '0')))
            athlete = weekly.athlete; start = weekly.week_start; end = start + timedelta(days=6)
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Select a valid athlete and dates through today.')
    people = athletes.filter(pk=athlete.pk) if athlete else (athletes.none() if kind == 'progress' else athletes)
    report = snapshot_for_week(weekly) if weekly else build_snapshot(kind, request.user, gym_id, people, start, end)
    report.update(gym_name=Gym.objects.get(pk=gym_id).name,
        coach_name=request.user.get_full_name() or request.user.username,
        sender=getattr(settings, 'REPORT_EMAIL_FROM', ''), app_url=getattr(settings, 'REPORT_EMAIL_APP_URL', ''))
    if request.method == 'POST':
        if request.POST.get('action') != 'prepare':
            return HttpResponseBadRequest('Choose Prepare email.')
        if not report['athlete_ids']:
            return HttpResponseBadRequest('No authorized athletes are available.')
        fingerprint = hashlib.sha256(json.dumps({'report': report, 'weekly': weekly.pk if weekly else None}, sort_keys=True).encode('utf-8')).hexdigest()
        draft, _ = EmailReportDraft.objects.get_or_create(gym_id=gym_id, coach=request.user, fingerprint=fingerprint, defaults={
            'report_key': kind, 'athlete': athlete, 'snapshot': report, 'weekly_summary': weekly,
            'publication': weekly.published_at if weekly else None})
        return redirect('practice_focus:email_report_detail', draft_id=draft.pk)
    return render(request, 'practice_focus/email_preview.html', {
        'report': report, 'kind': kind, 'athletes': athletes, 'athlete': athlete,
        'weekly': weekly, 'start_date': start, 'end_date': end, 'can_prepare': bool(report['athlete_ids'])})


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def email_report_detail(request, draft_id):
    gym_id, athletes = email_roster(request.user)
    draft = get_object_or_404(EmailReportDraft.objects.select_related('coach', 'gym', 'weekly_summary'), pk=draft_id, coach=request.user, gym_id=gym_id)
    problem = draft_problem(draft, request.user, gym_id, athletes)
    if request.method == 'POST':
        if request.POST.get('action') != 'send' or request.POST.get('version') != draft.created_at.isoformat():
            return HttpResponseBadRequest('Reload the preview before sending.')
        mode = request.POST.get('recipients')
        if mode not in ('self', 'parents') or (mode == 'parents' and not draft.athlete_id):
            return HttpResponseBadRequest('Select a permitted recipient group.')
        outcome = send_report(draft, mode, gym_id, athletes)
        if outcome['submitted']:
            messages.success(request, f"{outcome['submitted']} report email(s) submitted to the email provider.")
        if outcome.get('skipped'):
            messages.info(request, f"{outcome['skipped']} parent(s) have report email turned off.")
        if outcome.get('queued'):
            messages.success(request, f"{outcome['queued']} report(s) queued for parents’ weekly summaries.")
        if outcome['remaining']:
            messages.info(request, 'Some emails are still unsent or processing. Send again to continue; submitted emails are skipped.')
        if outcome['error']:
            messages.error(request, outcome['error'])
        if not any(outcome.values()):
            messages.info(request, 'This preview has already been emailed to the selected recipients.')
        return redirect(request.path)
    return render(request, 'practice_focus/email_detail.html', {
        'draft': draft, 'report': draft.snapshot, 'problem': problem,
        'configuration_problem': email_configuration(), 'parent_recipients': recipients_for(draft, 'parents'),
        'self_recipients': recipients_for(draft, 'self'), 'deliveries': draft.deliveries.select_related('recipient')})
