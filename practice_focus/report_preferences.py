from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from gyms.tenant import single_active_gym_id
from .models import CoachReportPreference


def report_gym_id(user):
    if not user.is_authenticated or not user.is_active or user.role not in ('coach', 'head_coach'):
        return None
    return single_active_gym_id(user, ['coach', 'head_coach'])


def show_group_averages(user, gym_id=None):
    active_gym = report_gym_id(user)
    if active_gym is None or (gym_id is not None and active_gym != gym_id):
        return False
    value = CoachReportPreference.objects.filter(gym_id=active_gym, coach=user).values_list('show_group_averages', flat=True).first()
    return True if value is None else value


class CoachReportPreferenceForm(forms.Form):
    show_group_averages = forms.BooleanField(
        required=False, label='Show group averages in reports',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'aria-describedby': 'report-sharing-help'}),
    )


@login_required
@require_POST
def save_report_settings(request):
    gym_id = report_gym_id(request.user)
    if gym_id is None:
        return HttpResponseForbidden('Only an active coach with one active gym can change report settings.')
    form = CoachReportPreferenceForm(request.POST, prefix='reports')
    if form.is_valid():
        CoachReportPreference.objects.update_or_create(
            gym_id=gym_id, coach=request.user,
            defaults={'show_group_averages': form.cleaned_data['show_group_averages']},
        )
        messages.success(request, 'Your report settings have been saved.')
    else:
        messages.error(request, 'Please check your report settings and try again.')
    return redirect('account_settings')
