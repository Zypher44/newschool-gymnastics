"""Public lead capture and a platform-owner inbox; no automatic outbound mail."""
from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .enquiry_forms import PublicEnquiryForm, TOKEN_SALT
from .models import PublicEnquiry


@never_cache
@require_http_methods(['GET', 'POST'])
def enquiry(request, kind='demo'):
    initial_kind = request.GET.get('topic', kind)
    if initial_kind not in PublicEnquiry.Kind.values:
        initial_kind = kind
    initial = {
        'kind': initial_kind,
        'submission_token': signing.dumps(str(uuid4()), salt=TOKEN_SALT),
    }
    form = PublicEnquiryForm(request.POST if request.method == 'POST' else None, initial=initial)
    status = 200
    if request.method == 'POST' and form.is_valid():
        # A signed token makes browser retries idempotent. Never show a stored lead publicly.
        submission_id = form.cleaned_data['submission_token']
        if PublicEnquiry.objects.filter(submission_id=submission_id).exists():
            return redirect('public_enquiry_received')
        now = timezone.now().timestamp()
        recent = [ts for ts in request.session.get('public_enquiry_times', []) if now - ts < 600]
        if len(recent) >= 3:
            form.add_error(None, 'You have sent several requests. Please try again in 10 minutes.')
            status = 429
        else:
            values = {name: form.cleaned_data[name] for name in form.Meta.fields}
            PublicEnquiry.objects.get_or_create(submission_id=submission_id, defaults=values)
            request.session['public_enquiry_times'] = [*recent, now]
            return redirect('public_enquiry_received')
    return render(request, 'public/enquiry.html', {
        'form': form, 'is_demo': kind == 'demo',
    }, status=status)


@never_cache
@require_http_methods(['GET'])
def received(request):
    return render(request, 'public/enquiry_received.html')


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def inbox(request):
    # Gym directors and ordinary staff must not see another business's enquiries.
    if not request.user.is_active or not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        try:
            enquiry_id = int(request.POST.get('enquiry_id', ''))
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Choose a valid enquiry.')
        row = get_object_or_404(PublicEnquiry, pk=enquiry_id)
        status = request.POST.get('status')
        if status not in PublicEnquiry.Status.values:
            return HttpResponseBadRequest('Choose a valid status.')
        row.status = status
        row.save(update_fields=['status'])
        return redirect('public_enquiry_inbox')
    page = Paginator(PublicEnquiry.objects.all(), 25).get_page(request.GET.get('page'))
    return render(request, 'public/enquiry_inbox.html', {
        'page': page, 'statuses': PublicEnquiry.Status.choices,
    })
