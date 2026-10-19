from django.contrib.auth import get_user_model
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from gyms.models import Gym, GymMembership
from practice_hub.models import OnboardingProgress
from practice_hub.templatetags.practice_hub_tags import practice_hub_welcome


class GuideDismissTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Guide Gym')
        self.user = get_user_model().objects.create_user(username='guide-coach', role='coach')
        GymMembership.objects.create(user=self.user, gym=self.gym, role='coach')
        self.client.force_login(self.user)
        self.url = reverse('practice_hub:dismiss_guide')

    def test_dismiss_preserves_progress_and_hides_only_own_banner(self):
        progress = OnboardingProgress.objects.create(user=self.user, gym=self.gym,
            role='coach', completed_steps=['group'], current_step=2, version=3)
        other = get_user_model().objects.create_user(username='other-coach', role='coach')
        GymMembership.objects.create(user=other, gym=self.gym, role='coach')
        response = self.client.post(self.url, {'user_id': other.pk}, HTTP_ACCEPT='application/json')
        self.assertJSONEqual(response.content, {'dismissed': True})
        progress.refresh_from_db()
        self.assertEqual(progress.completed_steps, ['group'])
        self.assertEqual(progress.current_step, 2)
        self.assertEqual(progress.version, 4)
        self.assertIsNotNone(progress.dismissed_at)
        self.assertIsNone(progress.completed_at)
        request = RequestFactory().get('/')
        request.user = self.user
        request.session = self.client.session
        self.assertEqual(practice_hub_welcome({'request': request}), {})
        request.user = other
        self.assertTrue(practice_hub_welcome({'request': request})['show'])
        self.assertEqual(self.client.get(reverse('practice_hub:onboarding')).status_code, 200)

    def test_post_and_csrf_required(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertFalse(OnboardingProgress.objects.exists())

    def test_pending_user_can_dismiss_without_gym_progress(self):
        GymMembership.objects.all().delete()
        self.assertEqual(self.client.post(self.url, HTTP_ACCEPT='application/json').status_code, 200)
        self.assertTrue(self.client.session['practice_hub_dismissed_coach'])
        self.assertFalse(OnboardingProgress.objects.exists())

    def test_fallback_rejects_external_redirect(self):
        response = self.client.post(self.url, {'next': '//example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('example.com', response.url)
