from datetime import timedelta
from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import AthleteFeedback, PersonalMilestone, TrackedResult, WeeklyProgressSummary
from .engagement_access import coach_roster, family_roster
from .engagement_forms import FeedbackForm, MilestoneForm, WeeklyDraftForm
from .engagement_services import refresh_milestones, weekly_snapshot
from .report_preferences import show_group_averages


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def coach_feedback(request):
    gym_id, athletes = coach_roster(request.user)
    selection = request.POST.get('athlete') if request.method == 'POST' else request.GET.get('athlete')
    athlete = get_object_or_404(athletes, pk=selection) if selection else athletes.first()
    feedback_form, milestone_form = FeedbackForm(prefix='feedback'), MilestoneForm(prefix='milestone')
    if request.method == 'POST':
        if athlete is None: return HttpResponseBadRequest('Select an athlete.')
        if request.POST.get('action') == 'feedback':
            feedback_form = FeedbackForm(request.POST, prefix='feedback')
            if feedback_form.is_valid():
                AthleteFeedback.objects.create(gym_id=gym_id, athlete=athlete, coach=request.user, **feedback_form.cleaned_data)
                messages.success(request, 'Feedback saved. Private notes remain visible to coaches only.')
                return redirect(request.path + f'?athlete={athlete.pk}')
        elif request.POST.get('action') == 'milestone':
            milestone_form = MilestoneForm(request.POST, prefix='milestone')
            if milestone_form.is_valid():
                PersonalMilestone.objects.create(gym_id=gym_id, athlete=athlete, key='coach:' + str(uuid4()),
                    title=milestone_form.cleaned_data['title'], practice_date=timezone.localdate(), awarded_by=request.user)
                messages.success(request, 'Milestone approved and shared with this athlete and their linked parents.')
                return redirect(request.path + f'?athlete={athlete.pk}')
        else: return HttpResponseBadRequest('Choose a valid action.')
    notes = AthleteFeedback.objects.filter(gym_id=gym_id, athlete=athlete).select_related('coach')[:40] if athlete else []
    milestones = PersonalMilestone.objects.filter(gym_id=gym_id, athlete=athlete, active=True)[:40] if athlete else []
    return render(request, 'practice_focus/coach_feedback.html', locals())


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def review_queue(request):
    gym_id, athletes = coach_roster(request.user)
    query = TrackedResult.objects.filter(gym_id=gym_id, athlete__in=athletes, status='pending')
    if request.method == 'POST':
        try:
            ids = [int(pk) for pk in request.POST.getlist('results')]
            if not ids or len(set(ids)) != len(ids) or len(ids) > 100: raise ValueError()
            action = request.POST['action']
            if action not in ('approve', 'reject'): raise ValueError()
            with transaction.atomic():
                records = list(query.select_for_update().filter(pk__in=ids))
                if len(records) != len(ids):
                    return HttpResponse('One or more results were changed or are outside your roster. Refresh before reviewing.', status=409)
                corrections = {}
                for item in records:
                    value = request.POST.get(f'result_{item.pk}', item.details.get('result'))
                    if value not in ('wow', 'hit', 'missed'): raise ValueError()
                    corrections[item.pk] = value
                for item in records:
                    source = item.skill_result or item.routine_result
                    if source is None:
                        return HttpResponse('A result was removed. Refresh before reviewing.', status=409)
                for item in records:
                    source = item.skill_result or item.routine_result
                    if action == 'reject':
                        source.delete(); item.skill_result = None; item.routine_result = None; item.status = 'rejected'
                    else:
                        item.details.setdefault('original_result', item.details['result'])
                        item.details['result'] = corrections[item.pk]
                        source.result = corrections[item.pk]; source.save(update_fields=['result'])
                        item.status = 'approved'
                    item.reviewed_by = request.user; item.reviewed_at = timezone.now(); item.save()
                    refresh_milestones(gym_id, item.athlete_id, item.practice_date)
            messages.success(request, f'{len(records)} result(s) {"approved" if action == "approve" else "removed"}.')
            return redirect('practice_focus:review_queue')
        except (ValueError, TypeError, KeyError): return HttpResponseBadRequest('Select valid results and an action.')
    records = query.select_related('athlete', 'actor').order_by('practice_date', 'pk')[:100]
    pending_total = query.count()
    return render(request, 'practice_focus/review_queue.html', locals())


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def weekly_reports(request):
    gym_id, athletes = coach_roster(request.user)
    selection = request.POST.get('athlete') if request.method == 'POST' else request.GET.get('athlete')
    athlete = get_object_or_404(athletes, pk=selection) if selection else athletes.first()
    today = timezone.localdate()
    last_monday = today - timedelta(days=today.weekday() + 7)
    form = WeeklyDraftForm(initial={'week_start': last_monday})
    if request.method == 'POST':
        if not athlete: return HttpResponseBadRequest('Select an athlete.')
        form = WeeklyDraftForm(request.POST)
        if form.is_valid():
            week = form.cleaned_data['week_start']
            snapshot = weekly_snapshot(request.user, athlete, gym_id, week, athletes)
            with transaction.atomic():
                # Changing a draft also withdraws its previous publication until it is reviewed again.
                summary, _ = WeeklyProgressSummary.objects.update_or_create(gym_id=gym_id, athlete=athlete,
                    coach=request.user, week_start=week, defaults={'snapshot': snapshot,
                        'coach_feedback': form.cleaned_data['coach_feedback'], 'published_at': None})
            return redirect('practice_focus:weekly_report_detail', summary_id=summary.pk)
    summaries = WeeklyProgressSummary.objects.filter(gym_id=gym_id, coach=request.user, athlete__in=athletes).select_related('athlete')[:100]
    return render(request, 'practice_focus/weekly_reports.html', locals())


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def weekly_report_detail(request, summary_id):
    staff = request.user.role in ('coach', 'head_coach')
    if staff:
        gym_id, athletes = coach_roster(request.user)
        query = WeeklyProgressSummary.objects.filter(gym_id=gym_id, coach=request.user, athlete__in=athletes)
    else:
        gym_id, athletes = family_roster(request.user)
        query = WeeklyProgressSummary.objects.filter(gym_id=gym_id, athlete__in=athletes, published_at__isnull=False)
    summary = get_object_or_404(query.select_related('athlete', 'coach'), pk=summary_id)
    if request.method == 'POST':
        if not staff: raise PermissionDenied('Only the authoring coach can publish this report.')
        with transaction.atomic():
            summary = query.select_for_update().get(pk=summary.pk)
            if request.POST.get('version') != summary.updated_at.isoformat():
                return HttpResponse('This summary changed. Reload the preview before publishing.', status=409)
            if request.POST.get('action') == 'publish': summary.published_at = timezone.now()
            elif request.POST.get('action') == 'withdraw': summary.published_at = None
            else: return HttpResponseBadRequest('Choose publish or withdraw.')
            summary.save(update_fields=['published_at', 'updated_at'])
        messages.success(request, 'Weekly report published to linked parents and the athlete.' if summary.published_at else 'Weekly report withdrawn.')
        return redirect(request.path)
    data = dict(summary.snapshot)
    if not show_group_averages(summary.coach, gym_id): data.pop('group', None)
    week_end = summary.week_start + timedelta(days=6)
    return render(request, 'practice_focus/weekly_report_detail.html', locals())


@login_required
@never_cache
def family_progress(request):
    gym_id, athletes = family_roster(request.user)
    selection = request.GET.get('athlete')
    athlete = get_object_or_404(athletes, pk=selection) if selection else athletes.first()
    # Explicit dictionaries keep private note fields out of all family template contexts.
    feedback = list(AthleteFeedback.objects.filter(gym_id=gym_id, athlete=athlete).exclude(shared_feedback='')
        .values('shared_feedback', 'created_at', 'coach__first_name', 'coach__last_name')[:40]) if athlete else []
    milestones = list(PersonalMilestone.objects.filter(gym_id=gym_id, athlete=athlete, active=True).values('id', 'title', 'practice_date')[:40]) if athlete else []
    summaries = WeeklyProgressSummary.objects.filter(gym_id=gym_id, athlete=athlete, published_at__isnull=False).select_related('coach')[:40] if athlete else []
    return render(request, 'practice_focus/family_progress.html', locals())
