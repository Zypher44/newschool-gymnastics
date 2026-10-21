from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership, TrainingGroup
from skill_tracker.models import Skill, Assignment
from .models import DailySurvey
from .forms import DailySurveyForm


class DailyCheckinTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Survey Gym')
        self.child = get_user_model().objects.create_user(username='checkin-child', role='athlete')
        GymMembership.objects.create(user=self.child, gym=self.gym, role='athlete')
        self.other = get_user_model().objects.create_user(username='another-child', role='athlete')
        skill = Skill.objects.create(gym=self.gym, event='beam', name='Handstand', key='handstand')
        self.assignment = Assignment.objects.create(skill=skill, athlete=self.child)
        self.foreign = Assignment.objects.create(skill=skill, athlete=self.other)
        self.client.force_login(self.child)
        self.url = reverse('submit_survey')
        self.data = {'energy': '1', 'sleep_quality': 'poor', 'body_feeling': 'pain',
            'practice_feeling': 'nervous', 'help_event': 'beam', 'help_skill': self.assignment.pk,
            'help_kind': 'confidence', 'coach_talk': 'before', 'soreness_area': 'wrist',
            'told_coach': 'no', 'worry_about': 'skill'}

    def test_new_checkin_keeps_history_and_saves_actionable_answers(self):
        old = DailySurvey.objects.create(athlete=self.child, survey_date=timezone.localdate()-timedelta(days=1),
            energy=4, soreness=2, stress=1, sleep_hours=9)
        before = DailySurvey.objects.values().get(pk=old.pk)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 302)
        new = DailySurvey.objects.get(survey_date=timezone.localdate())
        self.assertEqual(new.athlete, self.child)
        self.assertEqual(new.checkin_version, 2)
        self.assertEqual(new.help_skill, self.assignment)
        self.assertIsNone(new.soreness)
        self.assertIsNone(new.stress)
        self.assertIsNone(new.sleep_hours)
        self.assertIn('Talk before practice', new.checkin_flags)
        self.assertIn('Low energy', new.checkin_flags)
        self.assertEqual(before, DailySurvey.objects.values().get(pk=old.pk))
        self.assertEqual(self.client.post(self.url, self.data).status_code, 302)
        self.assertEqual(DailySurvey.objects.count(), 2)

    def test_invalid_tampered_and_missing_followup_rejected(self):
        for changes in [{'energy': '999'}, {'help_skill': self.foreign.pk}, {'told_coach': ''}]:
            response = self.client.post(self.url, {**self.data, **changes})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(DailySurvey.objects.exists())

    def test_hidden_followups_are_cleared_and_no_typing_required(self):
        form = DailySurveyForm({**self.data, 'body_feeling': 'good', 'practice_feeling': 'excited',
            'help_skill': '', 'help_event': 'none', 'coach_talk': 'no'}, user=self.child)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save(commit=False)
        self.assertEqual(saved.told_coach, '')
        self.assertEqual(saved.soreness_area, '')
        self.assertEqual(saved.help_kind, '')
        self.assertEqual(saved.worry_about, '')

    def test_get_readonly_csrf_and_role_boundaries(self):
        self.assertContains(self.client.get(self.url), 'How are you feeling today?')
        self.assertFalse(DailySurvey.objects.exists())
        client = Client(enforce_csrf_checks=True); client.force_login(self.child)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        coach = get_user_model().objects.create_user(username='not-an-athlete', role='coach')
        self.client.force_login(coach)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)

    def test_v2_summary_does_not_invent_readiness_or_break_reports(self):
        self.client.post(self.url, self.data)
        from coaches.views import build_dashboard_data
        from reports.services.athlete_progress import calculate_wellness_summary
        survey = DailySurvey.objects.get()
        self.assertIsNone(__import__('coaches.views', fromlist=['calculate_readiness_score']).calculate_readiness_score(survey))
        data = build_dashboard_data(get_user_model().objects.filter(pk=self.child.pk), timezone.localdate())
        self.assertTrue(any('Talk before practice' in row['message'] for row in data['coaching_priorities']))
        summary = calculate_wellness_summary(self.child, timezone.localdate(), timezone.localdate())
        self.assertIsNone(summary['average_soreness'])
        self.assertIsNone(summary['average_stress'])
