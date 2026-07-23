from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

User = get_user_model()

from .models import CoachAthleteAssignment, CoachNote, TeamEvent
from surveys.models import DailySurvey
from athletes.models import (
    AthleteProfile,
    AttendanceRecord,
    AthleteSkill,
    AthleteVideo,
    Skill,
)

from communications.dashboard import (
    get_dashboard_communication_data,
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


def get_coach_assignments(user):
    if user.role == 'head_coach':
        return CoachAthleteAssignment.objects.select_related('athlete', 'coach')

    return CoachAthleteAssignment.objects.filter(
        coach=user
    ).select_related('athlete', 'coach')


def get_pending_video_reviews(user):
    if user.role == 'head_coach':
        return AthleteVideo.objects.filter(
            review_status='not_reviewed'
        ).select_related(
            'athlete',
            'skill'
        ).order_by('-uploaded_at')[:10]

    return AthleteVideo.objects.filter(
        athlete__assigned_coaches__coach=user,
        review_status='not_reviewed'
    ).select_related(
        'athlete',
        'skill'
    ).distinct().order_by('-uploaded_at')[:10]


def get_team_skill_stats(athletes):
    team_skills = AthleteSkill.objects.filter(
        athlete__in=athletes
    )

    return {
        'skills_mastered': team_skills.filter(status='mastered').count(),
        'skills_competition_ready': team_skills.filter(status='competition_ready').count(),
        'skills_in_progress': team_skills.filter(status='in_progress').count(),
        'skills_not_started': team_skills.filter(status='not_started').count(),
    }


def get_upcoming_events(today):
    return TeamEvent.objects.filter(
        event_date__gte=today
    ).order_by('event_date', 'start_time')[:5]

def get_recent_activity(athletes, limit=12):
    activities = []

    recent_surveys = DailySurvey.objects.filter(
        athlete__in=athletes
    ).select_related(
        'athlete'
    ).order_by('-created_at')[:limit]

    for survey in recent_surveys:
        activities.append({
            'icon': '📝',
            'title': f'{survey.athlete.username} submitted a wellness survey',
            'description': (
                f'Energy {survey.energy} · '
                f'Soreness {survey.soreness} · '
                f'Stress {survey.stress}'
            ),
            'timestamp': survey.created_at,
            'url': reverse(
                'athlete_detail',
                args=[survey.athlete.id]
            ),
        })

    recent_videos = AthleteVideo.objects.filter(
        athlete__in=athletes
    ).select_related(
        'athlete',
        'skill',
        'uploaded_by'
    ).order_by('-uploaded_at')[:limit]

    for video in recent_videos:
        if video.skill:
            description = (
                f'{video.get_event_display()} · '
                f'{video.skill.name}'
            )
        else:
            description = video.get_event_display()

        activities.append({
            'icon': '🎥',
            'title': f'{video.athlete.username} had a video uploaded',
            'description': description,
            'timestamp': video.uploaded_at,
            'url': reverse(
                'athlete_detail',
                args=[video.athlete.id]
            ),
        })

    recent_notes = CoachNote.objects.filter(
        athlete__in=athletes
    ).select_related(
        'athlete',
        'coach'
    ).order_by('-created_at')[:limit]

    for note in recent_notes:
        note_preview = note.note

        if len(note_preview) > 80:
            note_preview = f'{note_preview[:80]}...'

        activities.append({
            'icon': '📌',
            'title': f'{note.coach.username} added a note for {note.athlete.username}',
            'description': note_preview,
            'timestamp': note.created_at,
            'url': reverse(
                'athlete_detail',
                args=[note.athlete.id]
            ),
        })

    activities.sort(
        key=lambda activity: activity['timestamp'],
        reverse=True
    )

    return activities[:limit]

def get_dashboard_notifications(
    coaching_priorities,
    pending_video_reviews,
    upcoming_events,
    today,
    limit=10
):
    notifications = []

    for priority in coaching_priorities:
        if priority['icon'] == '🎥':
            continue

        if priority['icon'] == '🔴':
            level = 'danger'
            label = 'Urgent'
        elif priority['icon'] == '🟠':
            level = 'warning'
            label = 'Attention'
        elif priority['icon'] == '❌':
            level = 'secondary'
            label = 'Missing'
        else:
            level = 'info'
            label = 'Notice'

        notifications.append({
            'level': level,
            'label': label,
            'icon': priority['icon'],
            'title': priority['athlete'].username,
            'message': priority['message'],
            'url': reverse(
                priority['url_name'],
                args=[priority['url_id']]
            ),
            'priority': 1 if level == 'danger' else 2,
        })

    video_count = len(pending_video_reviews)

    if video_count > 0:
        notifications.append({
            'level': 'primary',
            'label': 'Review',
            'icon': '🎥',
            'title': 'Video Reviews',
            'message': (
                f'{video_count} video'
                f'{"s" if video_count != 1 else ""} waiting for review'
            ),
            'url': '#videos-review',
            'priority': 3,
        })

    seven_days_from_today = today + timedelta(days=7)

    for event in upcoming_events:
        if event.event_date <= seven_days_from_today:
            days_until = (event.event_date - today).days

            if days_until == 0:
                event_message = 'Scheduled for today'
                priority = 1
                level = 'danger'
            elif days_until == 1:
                event_message = 'Scheduled for tomorrow'
                priority = 2
                level = 'warning'
            else:
                event_message = f'Scheduled in {days_until} days'
                priority = 4
                level = 'info'

            notifications.append({
                'level': level,
                'label': 'Event',
                'icon': '📅',
                'title': event.title,
                'message': event_message,
                'url': '#upcoming-events',
                'priority': priority,
            })

    notifications.sort(
        key=lambda notification: notification['priority']
    )

    return notifications[:limit]


def build_dashboard_data(assignments, today):
    athlete_data = []
    alerts = {}
    coaching_priorities = []

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
            issue = f"low energy for {low_energy_days} consecutive days"
            add_alert(alerts, athlete, issue)
            coaching_priorities.append({
                'icon': '🟠',
                'athlete': athlete,
                'message': issue,
                'url_name': 'athlete_detail',
                'url_id': athlete.id,
            })

        if high_soreness_days >= 2:
            issue = f"high soreness for {high_soreness_days} consecutive days"
            add_alert(alerts, athlete, issue)
            coaching_priorities.append({
                'icon': '🟠',
                'athlete': athlete,
                'message': issue,
                'url_name': 'athlete_detail',
                'url_id': athlete.id,
            })

        if high_stress_days >= 2:
            issue = f"high stress for {high_stress_days} consecutive days"
            add_alert(alerts, athlete, issue)
            coaching_priorities.append({
                'icon': '🟠',
                'athlete': athlete,
                'message': issue,
                'url_name': 'athlete_detail',
                'url_id': athlete.id,
            })

        if low_sleep_days >= 2:
            issue = f"low sleep for {low_sleep_days} consecutive days"
            add_alert(alerts, athlete, issue)
            coaching_priorities.append({
                'icon': '🟠',
                'athlete': athlete,
                'message': issue,
                'url_name': 'athlete_detail',
                'url_id': athlete.id,
            })

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
                coaching_priorities.append({
                    'icon': '🔴',
                    'athlete': athlete,
                    'message': issue,
                    'url_name': 'athlete_detail',
                    'url_id': athlete.id,
                })

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

            coaching_priorities.append({
                'icon': '❌',
                'athlete': athlete,
                'message': 'missing wellness survey today',
                'url_name': 'athlete_detail',
                'url_id': athlete.id,
            })

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

    return {
        'athlete_data': athlete_data,
        'alerts': alerts.values(),
        'coaching_priorities': coaching_priorities,
        'total_athletes': total_athletes,
        'submitted_today': submitted_today,
        'missing_today': missing_today,
        'submission_percentage': submission_percentage,
        'red_flags': red_flags,
        'orange_flags': orange_flags,
        'yellow_flags': yellow_flags,
        'green_flags': green_flags,
        'team_readiness_score': team_readiness_score,
    }


@login_required
def coach_dashboard(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    today = timezone.now().date()

    assignments = get_coach_assignments(request.user)
    athletes = [assignment.athlete for assignment in assignments]

    pending_video_reviews = get_pending_video_reviews(request.user)
    dashboard_data = build_dashboard_data(assignments, today)
    skill_stats = get_team_skill_stats(athletes)
    skill_chart_labels = [
        'Mastered',
        'Competition Ready',
        'In Progress',
        'Not Started',
    ]

    skill_chart_values = [
        skill_stats['skills_mastered'],
        skill_stats['skills_competition_ready'],
        skill_stats['skills_in_progress'],
        skill_stats['skills_not_started'],

    ]
    upcoming_events = get_upcoming_events(today)
    recent_activity = get_recent_activity(athletes)

    coaching_priorities = list(dashboard_data['coaching_priorities'])

    for video in pending_video_reviews:
        coaching_priorities.append({
            'icon': '🎥',
            'athlete': video.athlete,
            'message': f"video waiting for review: {video.title}",
            'url_name': 'athlete_detail',
            'url_id': video.athlete.id,
        })
    notifications = get_dashboard_notifications(
        coaching_priorities=coaching_priorities,
        pending_video_reviews=pending_video_reviews,
        upcoming_events=upcoming_events,
        today=today,
    )


    return render(request, 'coaches/dashboard.html', {
        **dashboard_data,
        **skill_stats,
        'coaching_priorities': coaching_priorities[:10],
        'upcoming_events': upcoming_events,
        'pending_video_reviews': pending_video_reviews,
        'videos_waiting_review_count': len(pending_video_reviews),
        'recent_activity': recent_activity,
        'notifications': notifications,
        'skill_chart_labels': skill_chart_labels,
        'skill_chart_values': skill_chart_values,
        'dashboard_communication': (
            get_dashboard_communication_data(
                request.user
            )
        ),
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
    assignments = get_coach_assignments(request.user)

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
            attempt_number=request.POST.get('attempt_number') or None,
            practice_date=request.POST.get('practice_date') or None,
            video_file=request.FILES.get('video_file'),
            technical_focus=request.POST.get('technical_focus', ''),
            review_status=request.POST.get('review_status', 'not_reviewed'),
            notes=request.POST.get('notes', ''),
            coach_feedback=request.POST.get('coach_feedback', ''),
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


@login_required
def update_video_review(request, athlete_id, video_id):
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

    video = AthleteVideo.objects.filter(
        id=video_id,
        athlete=athlete
    ).select_related('skill').first()

    if not video:
        return redirect('athlete_detail', athlete_id=athlete.id)

    if request.method == 'POST':
        video.review_status = request.POST.get('review_status', 'not_reviewed')
        video.technical_focus = request.POST.get('technical_focus', '')
        video.notes = request.POST.get('notes', '')
        video.coach_feedback = request.POST.get('coach_feedback', '')
        video.save()

    if video.skill:
        athlete_skill = AthleteSkill.objects.filter(
            athlete=athlete,
            skill=video.skill
        ).first()

        if athlete_skill:
            return redirect(
                'athlete_skill_detail',
                athlete_id=athlete.id,
                athlete_skill_id=athlete_skill.id
            )

    return redirect('athlete_detail', athlete_id=athlete.id)
@login_required
def athlete_search(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    query = request.GET.get('q', '').strip()

    assignments = get_coach_assignments(request.user)

    athletes = [
        assignment.athlete
        for assignment in assignments
    ]

    results = []

    if query:
        athlete_ids = [athlete.id for athlete in athletes]

        results = User.objects.filter(
            id__in=athlete_ids
        ).filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )

        if results.count() == 1:
            athlete = results.first()

            return redirect(
                'athlete_detail',
                athlete_id=athlete.id
            )

    return render(request, 'coaches/athlete_search.html', {
        'query': query,
        'results': results,
    })


@login_required
def team_skills_dashboard(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    assignments = get_coach_assignments(request.user)

    athletes = [
        assignment.athlete
        for assignment in assignments
    ]

    athlete_skills = AthleteSkill.objects.filter(
        athlete__in=athletes
    ).select_related(
        'athlete',
        'skill',
        'coach'
    ).order_by(
        'skill__event',
        'skill__name',
        'athlete__username'
    )

    event_labels = {
        'vault': 'Vault',
        'bars': 'Bars',
        'beam': 'Beam',
        'floor': 'Floor',
        'strength': 'Strength',
        'flexibility': 'Flexibility',
    }

    skills_by_event = {
        event_key: {
            'label': event_label,
            'skills': {},
            'total_records': 0,
            'completed_records': 0,
            'progress_percentage': 0,
        }
        for event_key, event_label in event_labels.items()
    }

    for athlete_skill in athlete_skills:
        event = athlete_skill.skill.event
        skill_id = athlete_skill.skill.id

        if event not in skills_by_event:
            continue

        if skill_id not in skills_by_event[event]['skills']:
            skills_by_event[event]['skills'][skill_id] = {
                'skill': athlete_skill.skill,
                'athlete_skills': [],
                'not_started': 0,
                'in_progress': 0,
                'consistent': 0,
                'competition_ready': 0,
                'mastered': 0,
                'total': 0,
                'completed': 0,
                'progress_percentage': 0,
            }

        skill_data = skills_by_event[event]['skills'][skill_id]

        skill_data['athlete_skills'].append(athlete_skill)
        skill_data['total'] += 1

        if athlete_skill.status in skill_data:
            skill_data[athlete_skill.status] += 1

        if athlete_skill.status in ['competition_ready', 'mastered']:
            skill_data['completed'] += 1

        skills_by_event[event]['total_records'] += 1

        if athlete_skill.status in ['competition_ready', 'mastered']:
            skills_by_event[event]['completed_records'] += 1

    for event_data in skills_by_event.values():
        for skill_data in event_data['skills'].values():
            if skill_data['total'] > 0:
                skill_data['progress_percentage'] = round(
                    (
                        skill_data['completed']
                        / skill_data['total']
                    ) * 100
                )

        if event_data['total_records'] > 0:
            event_data['progress_percentage'] = round(
                (
                    event_data['completed_records']
                    / event_data['total_records']
                ) * 100
            )

    team_skill_total = athlete_skills.count()

    team_skill_completed = athlete_skills.filter(
        status__in=['competition_ready', 'mastered']
    ).count()

    if team_skill_total > 0:
        team_skill_percentage = round(
            (team_skill_completed / team_skill_total) * 100
        )
    else:
        team_skill_percentage = 0

    status_totals = {
        'mastered': athlete_skills.filter(
            status='mastered'
        ).count(),

        'competition_ready': athlete_skills.filter(
            status='competition_ready'
        ).count(),

        'consistent': athlete_skills.filter(
            status='consistent'
        ).count(),

        'in_progress': athlete_skills.filter(
            status='in_progress'
        ).count(),

        'not_started': athlete_skills.filter(
            status='not_started'
        ).count(),
    }

    return render(request, 'coaches/team_skills.html', {
        'skills_by_event': skills_by_event,
        'team_skill_total': team_skill_total,
        'team_skill_completed': team_skill_completed,
        'team_skill_percentage': team_skill_percentage,
        'status_totals': status_totals,
        'total_athletes': len(athletes),
    })

@login_required
def athlete_search(request):
    if request.user.role not in ['coach', 'head_coach']:
        return render(request, 'coaches/not_allowed.html', {
            'role': request.user.role,
            'username': request.user.username,
        })

    query = request.GET.get('q', '').strip()

    if request.user.role == 'head_coach':
        athlete_ids = CoachAthleteAssignment.objects.values_list(
            'athlete_id',
            flat=True
        )
    else:
        athlete_ids = CoachAthleteAssignment.objects.filter(
            coach=request.user
        ).values_list(
            'athlete_id',
            flat=True
        )

    results = User.objects.none()

    if query:
        results = User.objects.filter(
            id__in=athlete_ids
        ).filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).order_by(
            'first_name',
            'last_name',
            'username'
        ).distinct()

        if results.count() == 1:
            athlete = results.first()

            return redirect(
                'athlete_detail',
                athlete_id=athlete.id
            )

    return render(request, 'coaches/athlete_search.html', {
        'query': query,
        'results': results,
    })