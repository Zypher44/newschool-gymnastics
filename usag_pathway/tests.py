from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from gyms.models import Gym, GymMembership

from .models import RequirementProgress, XcelRequirementProgress


class UsagGymIsolationTests(TestCase):
    def setUp(self):
        self.gym_a = Gym.objects.create(name='North Gym')
        self.gym_b = Gym.objects.create(name='South Gym')
        self.coach = User.objects.create_user(username='north_coach', password='test-password', role='head_coach')
        self.athlete_a = User.objects.create_user(username='north_athlete', password='test-password', role='athlete')
        self.athlete_b = User.objects.create_user(username='south_athlete', password='test-password', role='athlete')
        for user, gym, role in (
            (self.coach, self.gym_a, 'head_coach'),
            (self.athlete_a, self.gym_a, 'athlete'),
            (self.athlete_b, self.gym_b, 'athlete'),
        ):
            GymMembership.objects.create(user=user, gym=gym, role=role)
        self.client.force_login(self.coach)
        self.url = reverse('pathway:usag_level_detail', args=[6])

    def test_general_pathway_is_read_only_even_with_athlete_query(self):
        response = self.client.get(f'{self.url}?athlete={self.athlete_a.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'north_athlete')
        self.assertNotContains(response, 'south_athlete')
        self.assertNotContains(response, 'name="status"')
        self.assertNotContains(response, 'Review checklist')
        self.assertEqual(self.client.post(self.url, {
            'requirement_code': 'vault_1', 'status': 'ready',
        }).status_code, 403)
        self.assertFalse(RequirementProgress.objects.exists())

    def test_athlete_pathway_shows_own_gym_athlete(self):
        url = reverse('pathway:athlete_usag_level_detail', args=[self.athlete_a.pk, 6])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'north_athlete')
        self.assertNotContains(response, 'south_athlete')
        self.assertContains(response, 'name="status"')

    def test_cross_gym_assessment_is_rejected(self):
        url = reverse('pathway:athlete_usag_level_detail', args=[self.athlete_b.pk, 6])
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(url, {
            'requirement_code': 'vault_1', 'status': 'ready',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(RequirementProgress.objects.exists())

    def test_assessment_is_separate_and_scoped_to_gym(self):
        url = reverse('pathway:athlete_usag_level_detail', args=[self.athlete_a.pk, 6])
        response = self.client.post(url, {
            'requirement_code': 'vault_1', 'status': 'ready',
        })
        self.assertEqual(response.status_code, 302)
        progress = RequirementProgress.objects.get()
        self.assertEqual(progress.gym, self.gym_a)
        self.assertEqual(progress.athlete, self.athlete_a)
        self.assertEqual(response.url, url)

    def test_athlete_cannot_use_coach_assessment_page(self):
        self.client.force_login(self.athlete_a)
        url = reverse('pathway:athlete_usag_level_detail', args=[self.athlete_a.pk, 6])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {
            'requirement_code': 'vault_1', 'status': 'ready',
        }).status_code, 403)

    def test_ambiguous_gym_memberships_fail_closed(self):
        GymMembership.objects.create(
            gym=self.gym_b, user=self.coach, role='head_coach',
        )
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_overview_offers_all_ten_levels(self):
        response = self.client.get(reverse('pathway:pathway_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USAG Optional 2026–2030', count=1)
        for level in range(1, 11):
            self.assertContains(response, reverse('pathway:usag_level_detail', args=[level]))

    def test_xcel_divisions_appear_separately(self):
        response = self.client.get(reverse('pathway:pathway_overview'))
        self.assertEqual(response.status_code, 200)
        for division in ('bronze', 'silver', 'gold', 'platinum', 'diamond'):
            self.assertContains(
                response, reverse('pathway:xcel_division_detail', args=[division]),
            )

    def test_xcel_assessment_cannot_cross_gyms(self):
        url = reverse('pathway:athlete_xcel_division_detail', args=[self.athlete_b.pk, 'bronze'])
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(url, {
            'requirement_code': 'bars_1', 'status': 'ready',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(XcelRequirementProgress.objects.exists())

    def test_xcel_assessment_records_own_gym(self):
        url = reverse('pathway:athlete_xcel_division_detail', args=[self.athlete_a.pk, 'bronze'])
        response = self.client.post(url, {
            'requirement_code': 'bars_1', 'status': 'ready',
        })
        self.assertEqual(response.status_code, 302)
        row = XcelRequirementProgress.objects.get()
        self.assertEqual(row.gym, self.gym_a)
        self.assertEqual(row.division, 'bronze')
        self.assertEqual(response.url, url)

    def test_general_xcel_pathway_is_read_only(self):
        url = reverse('pathway:xcel_division_detail', args=['bronze'])
        response = self.client.get(f'{url}?athlete={self.athlete_a.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="status"')
        self.assertNotContains(response, 'north_athlete')
        self.assertEqual(self.client.post(url, {
            'requirement_code': 'bars_1', 'status': 'ready',
        }).status_code, 403)
        self.assertFalse(XcelRequirementProgress.objects.exists())

    def test_sapphire_is_not_available(self):
        url = reverse('pathway:xcel_division_detail', args=['sapphire'])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {
            'athlete': self.athlete_a.pk,
            'requirement_code': 'bars_1', 'status': 'ready',
        }).status_code, 404)
