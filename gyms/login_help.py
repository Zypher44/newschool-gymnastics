"""Director login assistance, scoped to the director's active gym."""
from django.contrib import messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import GymMembership
from .views import get_director_gym

MEMBER_ROLES = ['coach', 'head_coach', 'athlete', 'parent']


def director_gym(user):
    gym = get_director_gym(user)
    if not user.is_active or gym is None:
        raise PermissionDenied
    return gym


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def reset_person_password(request, membership_id):
    gym = director_gym(request.user)
    membership = get_object_or_404(
        GymMembership.objects.select_related('user').select_for_update(), pk=membership_id,
        gym=gym, role__in=MEMBER_ROLES)
    person = membership.user
    if person.role not in MEMBER_ROLES or person.is_staff or person.is_superuser:
        raise PermissionDenied
    if GymMembership.objects.filter(user=person, is_active=True,
                                    gym__is_active=True).exclude(gym=gym).exists():
        raise PermissionDenied('An account shared with another gym must use its own password recovery.')
    form = SetPasswordForm(person, request.POST if request.method == 'POST' else None)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control', 'autocomplete': 'new-password'})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            LogEntry.objects.create(
                user=request.user,
                content_type=ContentType.objects.get_for_model(person),
                object_id=str(person.pk), object_repr=str(person)[:200],
                action_flag=CHANGE, change_message='Password reset by gym director.')
        messages.success(request, f'Password updated for {person.username}. Share the new password with them.')
        return redirect('people_management')
    return render(request, 'gyms/reset_person_password.html', {
        'gym': gym, 'membership': membership, 'person': person, 'form': form})


@login_required
@require_http_methods(['GET', 'HEAD'])
def calendar_instead_of_events(request):
    director_gym(request.user)
    return redirect('gym_calendar')
