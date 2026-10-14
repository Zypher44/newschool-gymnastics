from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from gyms.models import Gym
from .engagement_access import coach_roster, family_roster
from .passport_forms import StampAwardForm
from .passport_models import PassportStamp, PassportAction
from .passport_services import passport_metrics, passport_cards, stamp_ready
from .passport_badge_services import badge_catalog, badge_snapshot


def select_athlete(athletes, raw):
    if raw:
        try:
            pk = int(raw)
        except (TypeError, ValueError):
            return None
        return get_object_or_404(athletes, pk=pk)
    return athletes.first()


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def coach_passport(request):
    gym_id, athletes = coach_roster(request.user)
    staff = True
    source = request.POST if request.method == 'POST' else request.GET
    athlete = select_athlete(athletes, source.get('athlete'))
    if source.get('athlete') and athlete is None:
        return HttpResponseBadRequest('Choose a valid athlete.')
    today = timezone.localdate()
    catalog = badge_catalog(gym_id, include_archived=True, include_deleted=True)
    award_catalog = {slot: definition for slot, definition in catalog.items() if definition['is_active']}
    metrics = passport_metrics(gym_id, athlete.pk, today) if athlete else {}
    cards = passport_cards(gym_id, athlete.pk, metrics, staff=True, catalog=catalog) if athlete else []
    selected_slot = request.GET.get('slot')
    if selected_slot not in award_catalog:
        selected_slot = next((c['slot'] for c in cards if not c['earned'] and c['ready']), next(iter(award_catalog), ''))
    version = next((c['version'] for c in cards if c['slot'] == selected_slot), 0)
    form = StampAwardForm(catalog=award_catalog, initial={'slot': selected_slot, 'award_date': today, 'version': version,
                          'definition_version': award_catalog.get(selected_slot, {}).get('definition_version', 0)})
    if request.method == 'POST':
        if not athlete or not source.get('athlete'):
            return HttpResponseBadRequest('Choose an athlete before awarding a stamp.')
        action = source.get('action')
        if action == 'award':
            form = StampAwardForm(request.POST, catalog=award_catalog)
            if form.is_valid():
                data = form.cleaned_data
                with transaction.atomic():
                    Gym.objects.select_for_update().get(pk=gym_id)
                    definition = badge_catalog(gym_id, include_archived=True).get(data['slot'])
                    if not definition or not definition['is_active'] or definition['definition_version'] != data['definition_version']:
                        return HttpResponse('This badge changed. Refresh before awarding it.', status=409)
                    # One locked child row serializes duplicate awards across coaches.
                    get_user_model().objects.select_for_update().get(pk=athlete.pk)
                    stamp = PassportStamp.objects.select_for_update().filter(gym_id=gym_id, athlete=athlete,
                        badge_code=definition['code'], variant=definition['variant']).first()
                    if stamp and stamp.revoked_at is None:
                        messages.info(request, 'This stamp is already in the athlete’s passport.')
                        return redirect(request.path + f'?athlete={athlete.pk}')
                    if data['version'] != (stamp.version if stamp else 0):
                        return HttpResponse('This stamp changed. Refresh before awarding it again.', status=409)
                    checked = passport_metrics(gym_id, athlete.pk, data['award_date'])
                    if not stamp_ready(definition, checked):
                        form.add_error('slot', 'The approved practice results or attendance have not reached this stamp’s target by the achievement date.')
                    else:
                        stamp = stamp or PassportStamp(gym_id=gym_id, athlete=athlete,
                            badge_code=definition['code'], variant=definition['variant'], version=0)
                        stamp.award_date, stamp.shared_note = data['award_date'], data['shared_note']
                        stamp.badge_snapshot = badge_snapshot(definition)
                        stamp.awarded_by, stamp.revoked_at = request.user, None
                        stamp.version += 1
                        stamp.save()
                        PassportAction.objects.create(stamp=stamp, actor=request.user, action='award', snapshot={
                            'title': definition['title'], 'date': data['award_date'].isoformat(),
                            'note': data['shared_note'], 'version': stamp.version, 'badge': stamp.badge_snapshot})
                        messages.success(request, definition['title'] + ' added to the athlete’s Practice Passport.')
                        return redirect(request.path + f'?athlete={athlete.pk}')
        elif action == 'withdraw':
            try:
                stamp_id, submitted_version = int(source.get('stamp', '')), int(source.get('version', ''))
            except (TypeError, ValueError):
                return HttpResponseBadRequest('Choose a valid stamp.')
            reason = source.get('reason', '').strip()
            if not reason or len(reason) > 300:
                return HttpResponseBadRequest('Enter a withdrawal reason of 1–300 characters.')
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(pk=athlete.pk)
                stamp = get_object_or_404(PassportStamp.objects.select_for_update(), pk=stamp_id, gym_id=gym_id, athlete=athlete)
                if stamp.version != submitted_version or stamp.revoked_at:
                    return HttpResponse('This stamp changed. Refresh before withdrawing it.', status=409)
                stamp.revoked_at = timezone.now(); stamp.version += 1
                stamp.save(update_fields=['revoked_at', 'version', 'updated_at'])
                PassportAction.objects.create(stamp=stamp, actor=request.user, action='withdraw',
                    snapshot={'reason': reason, 'version': stamp.version})
            messages.success(request, 'Stamp withdrawn. The correction remains in the coach history.')
            return redirect(request.path + f'?athlete={athlete.pk}')
        else:
            return HttpResponseBadRequest('Choose award or withdraw.')
    earned_count = sum(c['earned'] for c in cards)
    total_stamps = len(cards)
    badge_families = len({c['code'] for c in cards})
    card_data = [{k: c[k] for k in ('slot', 'title', 'rule', 'ready', 'earned', 'version', 'definition_version')} for c in cards]
    history = list(PassportAction.objects.filter(stamp__gym_id=gym_id, stamp__athlete=athlete)
                   .select_related('actor', 'stamp')[:30]) if athlete else []
    return render(request, 'practice_focus/passport.html', locals())


@login_required
@never_cache
@require_http_methods(['GET'])
def family_passport(request):
    gym_id, athletes = family_roster(request.user)
    staff = False
    athlete = select_athlete(athletes, request.GET.get('athlete'))
    if request.GET.get('athlete') and athlete is None:
        return HttpResponseBadRequest('Choose a valid athlete.')
    today = timezone.localdate()
    metrics = passport_metrics(gym_id, athlete.pk, today) if athlete else {}
    cards = passport_cards(gym_id, athlete.pk, metrics) if athlete else []
    earned_count = sum(c['earned'] for c in cards)
    total_stamps = len(cards)
    badge_families = len({c['code'] for c in cards})
    adventures = sorted([c for c in cards if not c['earned'] and not c['manual']],
                        key=lambda c: (not c['ready'], -c['percent'], c['target']))[:2]
    celebrations = [{'id': f"{c['award']['id']}:{c['award']['version']}", 'title': c['title'], 'slot': c['slot']}
                    for c in cards if c['earned']]
    celebration_scope = f'{gym_id}:{request.user.pk}:{athlete.pk}' if athlete else ''
    return render(request, 'practice_focus/passport.html', locals())
