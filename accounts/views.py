from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AccountProfileForm, StyledPasswordChangeForm


def _sync_legacy_phone(user):
    """Keep existing role profiles compatible during the transition."""
    profile = None

    if user.role == 'parent':
        profile = getattr(user, 'parent_profile', None)
    elif user.role in {'coach', 'head_coach'}:
        profile = getattr(user, 'coach_profile', None)

    if profile is not None and profile.phone != user.phone:
        profile.phone = user.phone
        profile.save(update_fields=['phone'])


@login_required
def account_settings(request):
    profile_form = AccountProfileForm(
        instance=request.user,
        user=request.user,
        prefix='profile',
    )
    password_form = StyledPasswordChangeForm(
        user=request.user,
        prefix='password',
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'profile':
            profile_form = AccountProfileForm(
                request.POST,
                instance=request.user,
                user=request.user,
                prefix='profile',
            )

            if profile_form.is_valid():
                user = profile_form.save()
                _sync_legacy_phone(user)
                messages.success(
                    request,
                    'Your account information has been updated.',
                )
                return redirect('account_settings')

        elif action == 'password':
            password_form = StyledPasswordChangeForm(
                user=request.user,
                data=request.POST,
                prefix='password',
            )

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(
                    request,
                    'Your password has been changed securely.',
                )
                return redirect('account_settings')

    return render(request, 'accounts/account_settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
