from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from practice_focus.email_provider import EmailDeliveryError


@override_settings(REPORT_EMAIL_API_KEY='test-only', REPORT_EMAIL_FROM='Gym <test@example.com>',
                   REPORT_EMAIL_APP_URL='https://test.example.com')
class AccountRecoveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user('recovery-user', email='family@example.com',
            password='OriginalFixturePassword!128')
        self.sibling = get_user_model().objects.create_user('sibling-user', email='family@example.com',
            password='SiblingFixturePassword!123')
        self.url = reverse('password_reset')

    @patch('accounts.recovery.submit_email')
    def test_recovery_sends_only_for_matching_username_and_uses_canonical_url(self, send):
        response = self.client.post(self.url, {'username': self.user.username, 'email': self.user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        send.assert_called_once()
        payload = send.call_args.args[0]
        self.assertEqual(payload['to'], [self.user.email])
        self.assertIn('https://test.example.com/accounts/password-reset/', payload['text'])
        self.assertNotIn(self.sibling.username, payload['text'])
        self.assertNotIn('OriginalFixturePassword', payload['text'])

    @patch('accounts.recovery.submit_email')
    def test_unknown_wrong_email_inactive_and_unusable_do_not_disclose_accounts(self, send):
        cases = [('missing', self.user.email), (self.user.username, 'wrong@example.com')]
        for username, email in cases:
            self.assertRedirects(self.client.post(self.url, {'username': username, 'email': email}),
                                 reverse('password_reset_done'))
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {'username': self.user.username, 'email': self.user.email})
        self.user.is_active = True
        self.user.set_unusable_password()
        self.user.save()
        self.client.post(self.url, {'username': self.user.username, 'email': self.user.email})
        send.assert_not_called()

    @patch('accounts.recovery.submit_email')
    def test_disabled_delivery_shows_help_and_never_sends_or_logs_tokens(self, send):
        with override_settings(REPORT_EMAIL_API_KEY=''):
            self.assertContains(self.client.get(self.url), 'Email recovery is not enabled')
            self.assertContains(self.client.post(self.url, {'username': self.user.username, 'email': self.user.email}),
                                'Contact your gym director')
        send.assert_not_called()

    @patch('accounts.recovery.submit_email', side_effect=EmailDeliveryError('provider failure'))
    def test_provider_failure_and_rate_limit_have_same_generic_response(self, send):
        for _ in range(7):
            self.assertRedirects(self.client.post(self.url, {'username': self.user.username, 'email': self.user.email}),
                                 reverse('password_reset_done'))
        self.assertEqual(send.call_count, 5)

    def test_token_changes_only_target_password_and_cannot_be_reused(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(url)
        clean_url = response.url
        self.assertNotContains(self.client.get(clean_url), 'already used')
        self.client.post(clean_url, {'new_password1': 'ReplacementFixturePassword!849',
                                     'new_password2': 'ReplacementFixturePassword!849'})
        self.user.refresh_from_db()
        self.sibling.refresh_from_db()
        self.assertTrue(self.user.check_password('ReplacementFixturePassword!849'))
        self.assertTrue(self.sibling.check_password('SiblingFixturePassword!123'))
        other_client = Client()
        self.assertContains(other_client.get(url), 'already used')

    def test_csrf_and_expired_token(self):
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.post(self.url, {'username': self.user.username, 'email': self.user.email}).status_code, 403)
        token = default_token_generator.make_token(self.user)
        self.user.set_password('ChangedFixturePassword!123')
        self.user.save()
        url = reverse('password_reset_confirm', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(self.user.pk)), 'token': token})
        self.assertContains(self.client.get(url), 'already used')
