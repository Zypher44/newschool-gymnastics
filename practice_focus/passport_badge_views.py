from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse
from gyms.models import Gym
from .access import coach_gym_id
from .passport_badge_models import PassportBadgeDefinition
from .passport_badge_forms import BadgeEditorForm
from .passport_badge_services import badge_catalog


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def badge_editor(request):
    gym_id = coach_gym_id(request.user)
    catalog = badge_catalog(gym_id, include_archived=True)
    slot = (request.POST if request.method == 'POST' else request.GET).get('slot', '')
    definition = catalog.get(slot) if slot else None
    if slot and not definition:
        raise Http404('Badge not found in your gym.')
    form = BadgeEditorForm(initial={'title': definition['title'], 'icon': definition['icon'],
        'description': definition['rule'], 'is_active': definition['is_active'],
        'version': definition['definition_version']} if definition else {'version': 0, 'is_active': True})
    if request.method == 'POST':
        if request.POST.get('action') != 'save':
            return HttpResponseBadRequest('Choose save.')
        form = BadgeEditorForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                # Catalog edits and awards share this lock so an archived badge cannot be awarded in a race.
                Gym.objects.select_for_update().get(pk=gym_id)
                current = badge_catalog(gym_id, include_archived=True).get(slot) if slot else None
                if data['version'] != (current['definition_version'] if current else 0):
                    return HttpResponse('This badge changed. Refresh before saving.', status=409)
                if slot and current is None:
                    raise Http404('Badge not found in your gym.')
                if slot:
                    badge = PassportBadgeDefinition.objects.filter(gym_id=gym_id, code=current['code'], variant=current['variant']).first()
                else:
                    badge = None
                badge = badge or PassportBadgeDefinition(gym_id=gym_id,
                    code=current['code'] if current else 'custom_' + uuid4().hex[:16],
                    variant=current['variant'] if current else 'earned', created_by=request.user, version=0)
                badge.title, badge.icon, badge.description = data['title'], data['icon'], data['description']
                badge.is_active, badge.updated_by = data['is_active'], request.user
                badge.version += 1
                badge.save()
            messages.success(request, 'Badge saved. Existing earned stamps keep their original details.')
            return redirect(request.path)
    badges = list(catalog.values())
    return render(request, 'practice_focus/badge_editor.html', locals())


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def badge_delete(request, code, variant):
    gym_id = coach_gym_id(request.user)
    slot = code + ':' + variant
    definition = badge_catalog(gym_id, include_archived=True, include_deleted=request.method == 'POST').get(slot)
    if not definition:
        raise Http404('Badge not found in your gym.')
    if request.method == 'GET':
        return render(request, 'practice_focus/badge_delete.html', {'definition': definition})
    if request.POST.get('action') != 'delete':
        return HttpResponseBadRequest('Confirm badge deletion.')
    try:
        submitted_version = int(request.POST.get('version', ''))
        if submitted_version < 0:
            raise ValueError
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Choose a valid badge version.')
    with transaction.atomic():
        Gym.objects.select_for_update().get(pk=gym_id)
        definition = badge_catalog(gym_id, include_archived=True, include_deleted=True).get(slot)
        if not definition:
            raise Http404('Badge not found in your gym.')
        if definition['deleted']:
            messages.info(request, 'This badge has already been deleted.')
            return redirect(reverse('practice_focus:badge_editor'))
        if definition['definition_version'] != submitted_version:
            return HttpResponse('This badge changed. Refresh before deleting it.', status=409)
        badge = PassportBadgeDefinition.objects.filter(gym_id=gym_id, code=code, variant=variant).first()
        badge = badge or PassportBadgeDefinition(gym_id=gym_id, code=code, variant=variant,
            title=definition['title'], icon=definition['icon'], description=definition['rule'],
            created_by=request.user, version=0)
        badge.deleted_at, badge.is_active, badge.updated_by = timezone.now(), False, request.user
        badge.version += 1
        badge.save()
    messages.success(request, 'Badge deleted from your gym’s library. Athletes keep any stamps they have already earned.')
    return redirect(reverse('practice_focus:badge_editor'))
