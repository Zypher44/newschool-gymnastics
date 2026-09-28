from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from .models import TestingExercise, TestingSession
from .views import get_authorized_session


class TestingGymIsolationTests(TestCase):
    def test_head_coach_cannot_open_foreign_session_or_edit_exercise(self):
        User = get_user_model()
        north = Gym.objects.create(name='North')
        south = Gym.objects.create(name='South')
        coach_n = User.objects.create_user('north_head', password='pass', role='head_coach')
        coach_s = User.objects.create_user('south_head', password='pass', role='head_coach')
        GymMembership.objects.create(gym=north, user=coach_n, role='head_coach')
        GymMembership.objects.create(gym=south, user=coach_s, role='head_coach')
        session_s = TestingSession.objects.create(
            gym=south, title='South session', testing_date=date(2026, 9, 25),
            created_by=coach_s,
        )
        exercise_s = TestingExercise.objects.create(
            gym=south, name='South exercise', created_by=coach_s,
        )
        session_n = TestingSession.objects.create(
            gym=north, title='North session', testing_date=date(2026, 9, 25),
            created_by=coach_n,
        )
        self.assertEqual(get_authorized_session(coach_n, session_n.pk), session_n)
        self.client.force_login(coach_n)
        self.assertEqual(self.client.get(reverse('testing_session_detail', args=[session_s.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('edit_testing_exercise', args=[exercise_s.pk])).status_code, 404)
