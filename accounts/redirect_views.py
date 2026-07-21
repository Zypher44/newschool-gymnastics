from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def role_redirect(request):
    """
    Redirect users to the dashboard assigned to their role.

    Role takes priority over Django superuser status so that
    superusers can still test coach, athlete, and parent portals.
    """

    user = request.user
    role = getattr(user, 'role', None)

    if role in ['coach', 'head_coach']:
        return redirect('coach_dashboard')

    if role == 'athlete':
        return redirect('athlete_dashboard')

    if role == 'parent':
        return redirect('parent_dashboard')

    if role == 'admin':
        return redirect('/admin/')

    if user.is_superuser:
        return redirect('/admin/')

    return render(
        request,
        'accounts/no_role.html',
        {
            'username': user.username,
            'role': role,
        }
    )