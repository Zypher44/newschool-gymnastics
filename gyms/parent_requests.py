"""Director review queue linked from family connection notifications."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .views import get_director_gym, pending_gym_parent_links


@login_required
@never_cache
@require_GET
def parent_connection_requests(request):
    gym = get_director_gym(request.user)
    if gym is None or not request.user.is_active:
        raise Http404
    links = pending_gym_parent_links(gym).filter(
        parent__is_active=True, athlete__is_active=True,
        parent__role='parent', athlete__role='athlete',
    )
    return render(request, 'gyms/parent_connection_requests.html', {
        'gym': gym, 'pending_parent_links': links,
    })
