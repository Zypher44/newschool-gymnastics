from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from .models import DailyRoutineSession


class RoutineGymIsolationTests(TestCase):
    def test_coach_cannot_post_attempt_into_other_gyms_session(self):
        User = get_user_model()
        north = Gym.objects.create(name='North')
        south = Gym.objects.create(name='South')
        coach = User.objects.create_user('north_coach', password='pass', role='coach')
        athlete = User.objects.create_user('north_athlete', password='pass', role='athlete')
        GymMembership.objects.create(gym=north, user=coach, role='coach')
        GymMembership.objects.create(gym=north, user=athlete, role='athlete')
        other_session = DailyRoutineSession.objects.create(gym=south, practice_date=date(2026, 9, 25))
        self.client.force_login(coach)
        response = self.client.post(reverse('routine_tracker:add_routine_attempt'), {
            'session_id': other_session.pk, 'athlete_id': athlete.pk,
            'event': 'vault', 'result': 'hit',
        })
        self.assertEqual(response.status_code, 404)
