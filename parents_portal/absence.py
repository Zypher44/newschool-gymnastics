from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from coaches.audiences import visible_events
from gyms.tenant import single_active_gym_id
from gyms.models import TrainingGroupAthlete
from .models import PracticeAbsenceNotice
from .selection import children_for, selected_child


class NoticeForm(forms.ModelForm):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)
    class Meta:
        model = PracticeAbsenceNotice
        fields = ['athlete', 'practice_date', 'event', 'status', 'expected_arrival', 'note']
        widgets = {'practice_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_arrival': forms.TimeInput(attrs={'type': 'time'}), 'note': forms.Textarea(attrs={'rows': 2, 'maxlength': 500})}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        ids = [child.pk for child in children_for(request)]
        self.fields['athlete'].queryset = get_user_model().objects.filter(pk__in=ids)
        self.fields['athlete'].label_from_instance = lambda child: child.get_full_name() or child.username
        self.fields['event'].queryset = visible_events(request.user).filter(event_date__gte=timezone.localdate())
        self.fields['event'].required = False
        self.fields['event'].empty_label = 'Practice date only (no calendar event)'
        self.fields['note'].label = 'Optional note for the coaching team'
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput): field.widget.attrs['class'] = 'form-control'

    def clean(self):
        data = super().clean()
        day, event, athlete = data.get('practice_date'), data.get('event'), data.get('athlete')
        if day and (day < timezone.localdate() or day > timezone.localdate() + timedelta(days=366)):
            self.add_error('practice_date', 'Choose today or a date within the next year.')
        if event and day and event.event_date != day:
            self.add_error('event', 'This event is on a different date.')
        if event and athlete and event.training_group_id and not TrainingGroupAthlete.objects.filter(
                athlete=athlete, group=event.training_group, is_active=True, group__is_active=True).exists():
            self.add_error('event', 'This event is not for the selected child’s group.')
        if data.get('status') != 'late': data['expected_arrival'] = None
        if data.get('status') == 'cancelled': data['note'] = ''
        return data


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def parent_absence(request):
    if request.user.role != 'parent' or not request.user.is_active: raise Http404
    gym_id = single_active_gym_id(request.user, ['parent'])
    if gym_id is None: raise Http404
    children = children_for(request)
    child = selected_child(request)
    notices = PracticeAbsenceNotice.objects.filter(gym_id=gym_id, athlete__in=children)
    initial = {'athlete': child, 'practice_date': timezone.localdate(), 'version': 0}
    event_id = request.GET.get('event')
    if event_id and event_id.isdigit():
        event = visible_events(request.user).filter(pk=event_id).first()
        if event: initial.update(event=event, practice_date=event.event_date)
    edit = notices.filter(pk=request.GET.get('edit')).first() if request.GET.get('edit', '').isdigit() else None
    if edit: initial.update(athlete=edit.athlete, practice_date=edit.practice_date, event=edit.event,
        status=edit.status, expected_arrival=edit.expected_arrival, note=edit.note, version=edit.version)
    instance = None
    if request.method == 'POST':
        from django.utils.dateparse import parse_date
        try:
            posted_day = parse_date(request.POST.get('practice_date', ''))
        except ValueError:
            posted_day = None
        posted_child = request.POST.get('athlete', '')
        if posted_day and posted_child.isdigit():
            instance = notices.filter(athlete_id=posted_child, practice_date=posted_day).first()
    form = NoticeForm(request.POST if request.method == 'POST' else None, request=request, initial=initial, instance=instance)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=data['athlete'].pk)
            current = notices.filter(athlete=data['athlete'], practice_date=data['practice_date']).first()
            if data['version'] != (current.version if current else 0):
                form.add_error(None, 'A notice already exists or was changed. Open it below to update the saved version.')
            else:
                notice = current or PracticeAbsenceNotice(gym_id=gym_id, athlete=data['athlete'], practice_date=data['practice_date'], version=0)
                for key in ('status', 'expected_arrival', 'note', 'event'): setattr(notice, key, data[key])
                notice.updated_by = request.user; notice.version += 1; notice.save()
                notify_coaches(notice, request.user)
                request.session['selected_child'] = notice.athlete_id
                messages.success(request, 'Coaching team notified. This is a planned notice; the coach records actual attendance at practice.')
                return redirect('parent_absence')
    return render(request, 'parents_portal/absence.html', {'form': form, 'notices': notices.filter(
        athlete=child, practice_date__gte=timezone.localdate()).select_related('athlete', 'event') if child else notices.none()})


def notify_coaches(notice, sender):
    from django.db.models import Q
    from communications.services import create_notification
    from gyms.models import TrainingGroup
    groups = TrainingGroup.objects.filter(athlete_assignments__athlete=notice.athlete,
        athlete_assignments__is_active=True, is_active=True, gym_id=notice.gym_id)
    staff = get_user_model().objects.filter(is_active=True, gym_memberships__gym_id=notice.gym_id,
        gym_memberships__is_active=True).filter(Q(role__in=['director', 'head_coach']) |
        Q(role='coach', assigned_athletes__athlete=notice.athlete) |
        Q(role='coach', training_group_assignments__group__in=groups)).distinct()
    for coach in staff:
        if single_active_gym_id(coach, [coach.role]) != notice.gym_id: continue
        create_notification(recipient=coach, sender=sender, notification_type='attendance', title='Parent attendance update',
            message=f'{notice.athlete.get_full_name() or notice.athlete.username}: {notice.get_status_display()} on {notice.practice_date:%b %d}.',
            link=reverse('gym_calendar') + '?month=' + notice.practice_date.strftime('%Y-%m'))
