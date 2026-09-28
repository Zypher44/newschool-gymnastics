from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership


class GymSignupFlowTests(TestCase):
    def signup(self, url, username, **extra):
        return self.client.post(reverse(url), {
            'username': username,
            'first_name': username,
            'last_name': 'Tester',
            'email': f'{username}@example.com',
            'password1': 'A-strong-passphrase-4871!',
            'password2': 'A-strong-passphrase-4871!',
            **extra,
        })

    def test_director_creates_their_own_gym(self):
        response = self.signup('director_signup', 'director_one', gym_name='North Gym')
        self.assertEqual(response.status_code, 302)
        director = get_user_model().objects.get(username='director_one')
        self.assertEqual(director.role, 'director')
        self.assertTrue(GymMembership.objects.filter(
            gym__name='North Gym', user=director, role='director', is_active=True
        ).exists())

    def test_member_selects_gym_but_waits_for_approval(self):
        north = Gym.objects.create(name='North Gym')
        south = Gym.objects.create(name='South Gym')
        response = self.signup('signup', 'parent_one', role='parent', gym=south.pk)
        self.assertEqual(response.status_code, 302)
        membership = GymMembership.objects.get(user__username='parent_one')
        self.assertEqual(membership.gym, south)
        self.assertNotEqual(membership.gym, north)
        self.assertFalse(membership.is_active)

    def test_cannot_choose_inactive_or_unknown_gym_or_director_role(self):
        inactive = Gym.objects.create(name='Closed Gym', is_active=False)
        self.signup('signup', 'parent_two', role='parent', gym=inactive.pk)
        self.assertFalse(get_user_model().objects.filter(username='parent_two').exists())
        self.signup('signup', 'director_fake', role='director', gym=inactive.pk)
        self.assertFalse(get_user_model().objects.filter(username='director_fake').exists())
