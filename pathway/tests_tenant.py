from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership


class PathwayGymIsolationTests(TestCase):
    def test_head_coach_cannot_open_another_gyms_athlete_editor(self):
        User = get_user_model()
        north = Gym.objects.create(name='North')
        south = Gym.objects.create(name='South')
        coach = User.objects.create_user('north_head', password='pass', role='head_coach')
        athlete = User.objects.create_user('south_athlete', password='pass', role='athlete')
        GymMembership.objects.create(gym=north, user=coach, role='head_coach')
        GymMembership.objects.create(gym=south, user=athlete, role='athlete')
        self.client.force_login(coach)
        self.assertEqual(self.client.get(reverse(
            'pathway:athlete_pathway_editor', args=[athlete.pk])).status_code, 404)
