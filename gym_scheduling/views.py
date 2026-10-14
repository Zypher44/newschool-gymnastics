from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from gyms.models import Gym
from gyms.tenant import single_active_gym_id
from .forms import GroupScheduleForm
from .models import GroupSchedule


@login_required
@require_http_methods(['GET', 'POST'])
def schedules(request, schedule_id=None):
    gym_id = single_active_gym_id(request.user, ['director']) if request.user.role == 'director' else None
    if gym_id is None:
        raise PermissionDenied('Only an active gym director can manage schedules.')
    # Serialize schedule writes within this gym so overlapping duplicate submissions
    # are revalidated after the preceding write on PostgreSQL.
    with transaction.atomic():
        if request.method == 'POST':
            Gym.objects.select_for_update().get(pk=gym_id)
        instance = (get_object_or_404(GroupSchedule, pk=schedule_id, group__gym_id=gym_id)
                    if schedule_id is not None else None)
        form = GroupScheduleForm(request.POST if request.method == 'POST' else None,
                                 instance=instance, gym_id=gym_id,
                                 initial={'start_date': timezone.localdate()} if instance is None else None)
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, 'Training-group schedule saved.')
            return redirect('group_schedules')
    items = GroupSchedule.objects.filter(group__gym_id=gym_id).select_related('group')
    return render(request, 'gym_scheduling/schedules.html', {
        'form': form, 'schedules': items, 'editing': instance,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def session_exceptions(request, schedule_id):
    from datetime import date
    from django.core.exceptions import ValidationError
    from .forms import ScheduleExceptionForm
    from .models import ScheduleException, check_session_conflict
    gym_id = single_active_gym_id(request.user, ['director']) if request.user.role == 'director' else None
    if gym_id is None:
        raise PermissionDenied('Only an active gym director can manage exceptions.')
    with transaction.atomic():
        if request.method == 'POST':
            Gym.objects.select_for_update().get(pk=gym_id)
        schedule = get_object_or_404(GroupSchedule, pk=schedule_id, group__gym_id=gym_id)
        initial = {}
        try:
            selected = date.fromisoformat(request.GET.get('date', ''))
            existing = schedule.exceptions.filter(date=selected).first()
            initial = {'date': selected}
            if existing:
                initial.update(action=existing.action, start_time=existing.start_time,
                               end_time=existing.end_time, note=existing.note)
        except ValueError:
            pass
        form = ScheduleExceptionForm(request.POST if request.method == 'POST' else None,
                                     schedule=schedule, initial=initial)
        if request.method == 'POST' and request.POST.get('operation') == 'restore':
            existing = get_object_or_404(ScheduleException, pk=request.POST.get('exception_id')
                                        if request.POST.get('exception_id', '').isdigit() else None,
                                        schedule=schedule)
            try:
                check_session_conflict(schedule, existing.date, schedule.start_time, schedule.end_time)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                existing.delete()
                messages.success(request, 'Regular session restored for this date.')
            return redirect('group_schedule_exceptions', schedule_id=schedule.pk)
        if request.method == 'POST' and form.is_valid():
            values = form.cleaned_data.copy()
            day = values.pop('date')
            ScheduleException.objects.update_or_create(schedule=schedule, date=day, defaults=values)
            messages.success(request, 'Single-day exception saved. Other dates are unchanged.')
            return redirect('group_schedule_exceptions', schedule_id=schedule.pk)
    return render(request, 'gym_scheduling/exceptions.html', {
        'schedule': schedule, 'form': form, 'exceptions': schedule.exceptions.all(),
    })
