from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import CoachAthleteAssignment, CoachNote, TeamEvent
from surveys.models import DailySurvey
from athletes.models import (
    AthleteProfile,
    AttendanceRecord,
    AthleteSkill,
    AthleteVideo,
    Skill,
)


def count_consecutive(surveys, condition):
    count = 0

    for survey in surveys:
        if condition(survey):
            count += 1
        else:
            break

    return count


def add_alert(alerts, athlete, issue):
    if athlete.id not in alerts:
        alerts[athlete.id] = {
            'athlete': athlete,
            'issues': []
        }

    alerts[athlete.id]['issues'].append(issue)


def calculate_readiness_score(survey):
    if not survey:
        return None

    if (
        survey.energy == 1 or
        survey.soreness == 5 or
        survey.stress == 5 or
        (survey.sleep_hours is not None and survey.sleep_hours < 6)
    ):
        return 25

    elif (
        survey.energy == 2 or
        survey.soreness == 4 or
        survey.stress == 4 or
        (survey.sleep_hours is not None and survey.sleep_hours < 7)
    ):
        return 50

    elif (
        survey.energy == 3 or
        survey.soreness == 3 or
        survey.stress == 3 or
        (survey.sleep_hours is not None and survey.sleep_hours < 8)
    ):
        return 75

    return 100


@login_required
def coach_dashboard(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    today = timezone.now().date()

    if request.user.role == 'head_coach':
        assignments = CoachAthleteAssignment.objects.select_related('athlete', 'coach')
    else:
        assignments = CoachAthleteAssignment.objects.filter(
            coach=request.user
        ).select_related('athlete', 'coach')

    athlete_data = []
    alerts = {}

    total_athletes = assignments.count()
    submitted_today = 0
    missing_today = 0

    red_flags = 0
    orange_flags = 0
    yellow_flags = 0
    green_flags = 0

    readiness_total = 0
    readiness_count = 0

    for assignment in assignments:
        athlete = assignment.athlete

        survey = DailySurvey.objects.filter(
            athlete=athlete,
            survey_date=today
        ).first()

        recent_surveys = list(
            DailySurvey.objects.filter(
                athlete=athlete
            ).order_by('-survey_date')[:7]
        )

        low_energy_days = count_consecutive(
            recent_surveys,
            lambda s: s.energy <= 2
        )

        high_soreness_days = count_consecutive(
            recent_surveys,
            lambda s: s.soreness >= 4
        )

        high_stress_days = count_consecutive(
            recent_surveys,
            lambda s: s.stress >= 4
        )

        low_sleep_days = count_consecutive(
            recent_surveys,
            lambda s: s.sleep_hours is not None and s.sleep_hours < 7
        )

        if low_energy_days >= 2:
            add_alert(alerts, athlete, f"low energy for {low_energy_days} consecutive days")

        if high_soreness_days >= 2:
            add_alert(alerts, athlete, f"high soreness for {high_soreness_days} consecutive days")

        if high_stress_days >= 2:
            add_alert(alerts, athlete, f"high stress for {high_stress_days} consecutive days")

        if low_sleep_days >= 2:
            add_alert(alerts, athlete, f"low sleep for {low_sleep_days} consecutive days")

        readiness_score = calculate_readiness_score(survey)

        if survey:
            submitted_today += 1
            readiness_count += 1

            athlete_alerts = []

            if survey.energy == 1:
                athlete_alerts.append("low energy today")

            if survey.soreness == 5:
                athlete_alerts.append("high soreness today")

            if survey.stress == 5:
                athlete_alerts.append("high stress today")

            if survey.sleep_hours is not None and survey.sleep_hours < 6:
                athlete_alerts.append("low sleep today")

            for issue in athlete_alerts:
                add_alert(alerts, athlete, issue)

            if readiness_score == 25:
                red_flags += 1
            elif readiness_score == 50:
                orange_flags += 1
            elif readiness_score == 75:
                yellow_flags += 1
            elif readiness_score == 100:
                green_flags += 1

            readiness_total += readiness_score

        else:
            missing_today += 1

        athlete_data.append({
            'athlete': athlete,
            'coach': assignment.coach,
            'survey': survey,
            'readiness_score': readiness_score,
        })

    if total_athletes > 0:
        submission_percentage = round((submitted_today / total_athletes) * 100)
    else:
        submission_percentage = 0

    if readiness_count > 0:
        team_readiness_score = round(readiness_total / readiness_count)
    else:
        team_readiness_score = 0

    upcoming_events = TeamEvent.objects.filter(
        event_date__gte=today
    ).order_by('event_date', 'start_time')[:5]

    return render(request, 'coaches/dashboard.html', {
        'athlete_data': athlete_data,
        'alerts': alerts.values(),
        'total_athletes': total_athletes,
        'submitted_today': submitted_today,
        'missing_today': missing_today,
        'submission_percentage': submission_percentage,
        'red_flags': red_flags,
        'orange_flags': orange_flags,
        'yellow_flags': yellow_flags,
        'green_flags': green_flags,
        'team_readiness_score': team_readiness_score,
        'upcoming_events': upcoming_events,
    })


@login_required
def athlete_detail(request, athlete_id):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.user.role == 'head_coach':
        assignment = CoachAthleteAssignment.objects.filter(
            athlete_id=athlete_id
        ).select_related('athlete', 'coach').first()
    else:
        assignment = CoachAthleteAssignment.objects.filter(
            coach=request.user,
            athlete_id=athlete_id
        ).select_related('athlete', 'coach').first()

    if not assignment:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete = assignment.athlete

    athlete_profile = AthleteProfile.objects.filter(
        user=athlete
    ).first()

    if request.method == 'POST':
        note_text = request.POST.get('note')

        if note_text:
            CoachNote.objects.create(
                athlete=athlete,
                coach=request.user,
                note=note_text
            )

        return redirect('athlete_detail', athlete_id=athlete.id)

    surveys = DailySurvey.objects.filter(
        athlete=athlete
    ).order_by('-survey_date')[:7]

    chart_surveys = list(reversed(surveys))

    chart_labels = [survey.survey_date.strftime("%b %d") for survey in chart_surveys]
    energy_data = [survey.energy for survey in chart_surveys]
    soreness_data = [survey.soreness for survey in chart_surveys]
    stress_data = [survey.stress for survey in chart_surveys]
    sleep_data = [
        float(survey.sleep_hours) if survey.sleep_hours is not None else 0
        for survey in chart_surveys
    ]

    notes = CoachNote.objects.filter(
        athlete=athlete
    ).select_related('coach')[:10]

    attendance_records = AttendanceRecord.objects.filter(
        athlete=athlete
    ).order_by('-attendance_date')[:10]

    attendance_total = AttendanceRecord.objects.filter(
        athlete=athlete
    ).count()

    attendance_present = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='present'
    ).count()

    attendance_late = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='late'
    ).count()

    attendance_absent = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='absent'
    ).count()

    attendance_excused = AttendanceRecord.objects.filter(
        athlete=athlete,
        status='excused'
    ).count()

    if attendance_total > 0:
        attendance_rate = round(((attendance_present + attendance_late) / attendance_total) * 100)
    else:
        attendance_rate = 0

    athlete_skills = AthleteSkill.objects.filter(
        athlete=athlete
    ).select_related('skill', 'coach')

    skills_by_event = {
        'vault': [],
        'bars': [],
        'beam': [],
        'floor': [],
        'strength': [],
        'flexibility': [],
    }

    for athlete_skill in athlete_skills:
        skills_by_event[athlete_skill.skill.event].append(athlete_skill)

    athlete_videos = AthleteVideo.objects.filter(
        athlete=athlete
    ).select_related('skill', 'uploaded_by')

    videos_by_event = {
        'vault': [],
        'bars': [],
        'beam': [],
        'floor': [],
        'strength': [],
        'flexibility': [],
        'other': [],
    }

    for video in athlete_videos:
        videos_by_event[video.event].append(video)

    return render(request, 'coaches/athlete_detail.html', {
        'athlete': athlete,
        'athlete_profile': athlete_profile,
        'coach': assignment.coach,
        'surveys': surveys,
        'notes': notes,
        'chart_labels': chart_labels,
        'energy_data': energy_data,
        'soreness_data': soreness_data,
        'stress_data': stress_data,
        'sleep_data': sleep_data,
        'attendance_records': attendance_records,
        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_late': attendance_late,
        'attendance_absent': attendance_absent,
        'attendance_excused': attendance_excused,
        'attendance_rate': attendance_rate,
        'skills_by_event': skills_by_event,
        'videos_by_event': videos_by_event,
    })


@login_required
def add_event(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.method == "POST":
        TeamEvent.objects.create(
            title=request.POST.get("title"),
            event_date=request.POST.get("event_date"),
            start_time=request.POST.get("start_time") or None,
            end_time=request.POST.get("end_time") or None,
            location=request.POST.get("location"),
            description=request.POST.get("description"),
            created_by=request.user,
        )

        return redirect("coach_dashboard")

    return render(request, "coaches/add_event.html")


@login_required
def take_attendance(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    today = timezone.now().date()

    if request.user.role == 'head_coach':
        assignments = CoachAthleteAssignment.objects.select_related('athlete', 'coach')
    else:
        assignments = CoachAthleteAssignment.objects.filter(
            coach=request.user
        ).select_related('athlete', 'coach')

    athletes = [assignment.athlete for assignment in assignments]

    existing_records = AttendanceRecord.objects.filter(
        athlete__in=athletes,
        attendance_date=today
    )

    attendance_map = {
        record.athlete_id: record
        for record in existing_records
    }

    if request.method == 'POST':
        for athlete in athletes:
            status = request.POST.get(f'status_{athlete.id}')
            notes = request.POST.get(f'notes_{athlete.id}', '')

            if status:
                AttendanceRecord.objects.update_or_create(
                    athlete=athlete,
                    attendance_date=today,
                    defaults={
                        'coach': request.user,
                        'status': status,
                        'notes': notes,
                    }
                )

        return redirect('coach_dashboard')

    athlete_attendance = []

    for athlete in athletes:
        athlete_attendance.append({
            'athlete': athlete,
            'record': attendance_map.get(athlete.id),
        })

    return render(request, 'coaches/take_attendance.html', {
        'today': today,
        'athlete_attendance': athlete_attendance,
    })


@login_required
def update_athlete_skill(request, athlete_id, athlete_skill_id):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.user.role == 'head_coach':
        assignment = CoachAthleteAssignment.objects.filter(
            athlete_id=athlete_id
        ).select_related('athlete').first()
    else:
        assignment = CoachAthleteAssignment.objects.filter(
            coach=request.user,
            athlete_id=athlete_id
        ).select_related('athlete').first()

    if not assignment:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete = assignment.athlete

    athlete_skill = AthleteSkill.objects.filter(
        id=athlete_skill_id,
        athlete=athlete
    ).select_related('skill').first()

    if not athlete_skill:
        return redirect('athlete_detail', athlete_id=athlete.id)

    if request.method == 'POST':
        athlete_skill.status = request.POST.get('status')
        athlete_skill.started_date = request.POST.get('started_date') or None
        athlete_skill.achieved_date = request.POST.get('achieved_date') or None
        athlete_skill.notes = request.POST.get('notes', '')
        athlete_skill.coach = request.user
        athlete_skill.save()

    return redirect('athlete_detail', athlete_id=athlete.id)


@login_required
def upload_athlete_video(request, athlete_id):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.user.role == 'head_coach':
        assignment = CoachAthleteAssignment.objects.filter(
            athlete_id=athlete_id
        ).select_related('athlete').first()
    else:
        assignment = CoachAthleteAssignment.objects.filter(
            coach=request.user,
            athlete_id=athlete_id
        ).select_related('athlete').first()

    if not assignment:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete = assignment.athlete
    skills = Skill.objects.all().order_by('event', 'name')

    if request.method == 'POST':
        skill_id = request.POST.get('skill')

        skill = None
        if skill_id:
            skill = Skill.objects.filter(id=skill_id).first()

        AthleteVideo.objects.create(
            athlete=athlete,
            uploaded_by=request.user,
            event=request.POST.get('event'),
            skill=skill,
            title=request.POST.get('title'),
            practice_date=request.POST.get('practice_date') or None,
            video_file=request.FILES.get('video_file'),
            notes=request.POST.get('notes', ''),
        )

        return redirect('athlete_detail', athlete_id=athlete.id)

    return render(request, 'coaches/upload_athlete_video.html', {
        'athlete': athlete,
        'skills': skills,
        'event_choices': AthleteVideo.EVENT_CHOICES,
    })

@login_required
def athlete_skill_detail(request, athlete_id, athlete_skill_id):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    if request.user.role == 'head_coach':
        assignment = CoachAthleteAssignment.objects.filter(
            athlete_id=athlete_id
        ).select_related('athlete').first()
    else:
        assignment = CoachAthleteAssignment.objects.filter(
            coach=request.user,
            athlete_id=athlete_id
        ).select_related('athlete').first()

    if not assignment:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    athlete = assignment.athlete

    athlete_skill = AthleteSkill.objects.filter(
        id=athlete_skill_id,
        athlete=athlete
    ).select_related('skill', 'coach').first()

    if not athlete_skill:
        return redirect('athlete_detail', athlete_id=athlete.id)

    skill_videos = AthleteVideo.objects.filter(
        athlete=athlete,
        skill=athlete_skill.skill
    ).select_related('uploaded_by').order_by('-practice_date', '-uploaded_at')

    return render(request, 'coaches/athlete_skill_detail.html', {
        'athlete': athlete,
        'athlete_skill': athlete_skill,
        'skill_videos': skill_videos,
    })

