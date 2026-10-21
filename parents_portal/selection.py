from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .access import get_approved_parent_links

FAMILY_PAGES = {'parent_dashboard', 'parent_conditioning_history', 'parent_video_library',
    'practice_focus:family_progress', 'practice_focus:family_passport',
    'practice_focus:journal_history', 'video_library:family_library', 'pathway:pathway_overview',
    'gym_calendar', 'parent_absence'}


def children_for(request):
    if not request.user.is_authenticated or request.user.role != 'parent' or not request.user.is_active:
        return []
    if not hasattr(request, '_family_children'):
        request._family_children = [link.athlete for link in get_approved_parent_links(request.user).order_by('athlete__first_name', 'athlete__last_name', 'athlete__username')]
    return request._family_children


def selected_child(request):
    children = children_for(request)
    match = getattr(request, 'resolver_match', None)
    route_child = match.kwargs.get('athlete_id') if match and match.view_name == 'routine_tracker:parent_routine_consistency' else None
    raw = route_child or request.GET.get('athlete') or request.session.get('selected_child')
    child = next((c for c in children if str(c.pk) == str(raw)), None)
    return child or (children[0] if children else None)


class FamilySelectionMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request): return self.get_response(request)
    def process_view(self, request, view, args, kwargs):
        if not request.user.is_authenticated or request.user.role != 'parent': return
        name = request.resolver_match.view_name
        if name not in FAMILY_PAGES: return
        children = children_for(request)
        raw = request.GET.get('athlete')
        if raw and not any(str(c.pk) == raw for c in children):
            raise Http404('This child is not connected to your account.')
        child = selected_child(request)
        if child:
            if raw: request.session['selected_child'] = child.pk
            query = request.GET.copy(); query['athlete'] = str(child.pk); request.GET = query


def family_context(request):
    children = children_for(request)
    return {'family_children': children, 'family_selected_child': selected_child(request) if children else None}


@login_required
@require_POST
def switch_child(request):
    child = next((c for c in children_for(request) if str(c.pk) == request.POST.get('athlete')), None)
    if child is None: raise Http404
    request.session['selected_child'] = child.pk
    messages.success(request, f"You're now viewing {child.get_full_name() or child.username}.")
    return redirect(reverse('account_settings') + '#family-view')
