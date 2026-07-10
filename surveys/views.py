from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import DailySurvey
from coaches.models import TeamEvent


@login_required
def submit_survey(request):
    if request.user.role != "athlete":
        return render(request, "surveys/not_allowed.html")

    if request.method == "POST":
        survey_date = timezone.now().date()

        existing_survey = DailySurvey.objects.filter(
            athlete=request.user,
            survey_date=survey_date
        ).first()

        if existing_survey:
            messages.error(request, "You already submitted a survey for today.")
            return redirect("submit_survey")

        DailySurvey.objects.create(
            athlete=request.user,
            survey_date=survey_date,
            energy=int(request.POST.get("energy", 3)),
            soreness=int(request.POST.get("soreness", 3)),
            stress=int(request.POST.get("stress", 3)),
            sleep_hours=request.POST.get("sleep_hours") or None,
            ate_well=request.POST.get("ate_well") == "on",
            hydrated=request.POST.get("hydrated") == "on",
            soreness_area=request.POST.get("soreness_area", ""),
            notes=request.POST.get("notes", ""),
        )

        return redirect("survey_success")

    upcoming_events = TeamEvent.objects.filter(
        event_date__gte=timezone.now().date()
    ).order_by("event_date", "start_time")[:5]

    return render(request, "surveys/submit_survey.html", {
        "upcoming_events": upcoming_events,
    })


@login_required
def survey_success(request):
    return render(request, "surveys/success.html")