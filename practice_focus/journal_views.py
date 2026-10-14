from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from .engagement_access import coach_roster, family_roster
from .journal_forms import JournalEntryForm, JournalHistoryForm
from .journal_models import AthleteJournalEntry


def journal_scope(user):
    if user.role in ('coach', 'head_coach'):
        gym_id, athletes = coach_roster(user)
        entries = AthleteJournalEntry.objects.filter(share_with_coaches=True)
    elif user.role in ('athlete', 'parent'):
        gym_id, athletes = family_roster(user)
        entries = AthleteJournalEntry.objects.all()
        if user.role == 'parent':
            entries = entries.filter(share_with_parents=True)
    else:
        raise PermissionDenied('Athlete, coach, or approved parent access is required.')
    return gym_id, athletes, entries.filter(gym_id=gym_id, athlete__in=athletes).select_related('athlete')


@login_required
@never_cache
@require_GET
def journal_history(request):
    gym_id, athletes, entries = journal_scope(request.user)
    owner = request.user.role == 'athlete'
    picker = athletes.filter(pk__in=entries.values('athlete_id')) if not owner else athletes
    form = JournalHistoryForm(request.GET)
    if form.is_valid():
        athlete_id = form.cleaned_data.get('athlete')
        if athlete_id:
            get_object_or_404(athletes, pk=athlete_id)
            entries = entries.filter(athlete_id=athlete_id)
        for key, lookup in [('start', 'entry_date__gte'), ('end', 'entry_date__lte')]:
            if form.cleaned_data.get(key):
                entries = entries.filter(**{lookup: form.cleaned_data[key]})
    else:
        entries = entries.none()
    # Only athletes with a shared entry appear in a viewer's journal picker.
    page = Paginator(entries, 15).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'practice_focus/journal_history.html', {
        'owner': owner, 'page': page, 'filter_form': form, 'athletes': picker,
        'selected_athlete': request.GET.get('athlete', ''), 'filter_query': query.urlencode(),
        'today': timezone.localdate(),
    })


@login_required
@never_cache
@require_GET
def journal_detail(request, entry_id):
    _, _, entries = journal_scope(request.user)
    entry = get_object_or_404(entries, pk=entry_id)
    return render(request, 'practice_focus/journal_detail.html', {
        'entry': entry, 'owner': request.user.role == 'athlete',
    })


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def journal_edit(request, entry_id=None):
    if request.user.role != 'athlete':
        raise PermissionDenied('Only athletes can write their own journal.')
    gym_id, athletes = family_roster(request.user)
    get_object_or_404(athletes, pk=request.user.pk)
    own_entries = AthleteJournalEntry.objects.filter(gym_id=gym_id, athlete=request.user)
    entry = get_object_or_404(own_entries, pk=entry_id) if entry_id is not None else None
    if request.method == 'GET' and entry is None and not request.GET.get('date'):
        today_entry = own_entries.filter(entry_date=timezone.localdate()).first()
        if today_entry:
            return redirect('practice_focus:journal_edit', entry_id=today_entry.pk)
    initial = {'entry_date': entry.entry_date if entry else timezone.localdate(),
               'version': entry.version if entry else 0}
    if request.method == 'GET' and entry is None and request.GET.get('date'):
        date_form = JournalHistoryForm({'start': request.GET['date']})
        if not date_form.is_valid() or date_form.cleaned_data['start'] > timezone.localdate():
            raise Http404('Choose today or an earlier date.')
        initial['entry_date'] = date_form.cleaned_data['start']
        existing = own_entries.filter(entry_date=initial['entry_date']).first()
        if existing:
            return redirect('practice_focus:journal_edit', entry_id=existing.pk)
    instance = entry or AthleteJournalEntry(gym_id=gym_id, athlete=request.user)
    form = JournalEntryForm(request.POST if request.method == 'POST' else None,
                            instance=instance, initial=initial)
    status = 200
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                locked = (own_entries.select_for_update().filter(pk=entry_id).first()
                          if entry_id is not None else
                          own_entries.select_for_update().filter(entry_date=form.cleaned_data['entry_date']).first())
                if entry_id is not None and locked is None:
                    raise Http404
                if locked is not None and (entry_id is None or locked.version != form.cleaned_data['version']):
                    raise ValidationError('An entry for this date has already been saved or changed in another tab. '
                        'Your answers are still below. Open the latest saved entry before making another edit.')
                if locked is None and form.cleaned_data['version'] != 0:
                    raise ValidationError('Reload the journal before saving a new entry.')
                saved = locked or AthleteJournalEntry(gym_id=gym_id, athlete=request.user)
                for field in JournalEntryForm.Meta.fields:
                    setattr(saved, field, form.cleaned_data[field])
                saved.version = locked.version + 1 if locked else 1
                saved.full_clean()
                saved.save()
            messages.success(request, 'Journal saved. You can read it again in your past entries.')
            return redirect('practice_focus:journal_detail', entry_id=saved.pk)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
            status = 409
    return render(request, 'practice_focus/journal_edit.html', {
        'form': form, 'entry': entry, 'owner': True, 'today': timezone.localdate(),
    }, status=status)
