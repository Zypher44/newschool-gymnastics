from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import DailySurvey
from .forms import DailySurveyForm


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def submit_survey(request):
    if request.user.role != 'athlete' or not request.user.is_active:
        return render(request, 'surveys/not_allowed.html', status=403)
    today = timezone.localdate()
    existing = DailySurvey.objects.filter(athlete=request.user, survey_date=today).first()
    form = DailySurveyForm(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST':
        if existing:
            messages.info(request, 'Your check-in is already saved for today.')
            return redirect('submit_survey')
        if form.is_valid():
            survey = form.save(commit=False)
            survey.athlete = request.user
            survey.survey_date = today
            try:
                with transaction.atomic():
                    survey.save()
            except IntegrityError:
                messages.info(request, 'Your check-in is already saved for today.')
                return redirect('submit_survey')
            return redirect('survey_success')
    return render(request, 'surveys/submit_survey.html', {'form': form, 'existing': existing, 'today': today})


@login_required
def survey_success(request):
    return render(request, 'surveys/success.html')
