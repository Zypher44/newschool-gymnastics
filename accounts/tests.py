from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='settings_parent',
            password='StrongTestPass123!',
            first_name='Old',
            last_name='Name',
            email='old@example.com',
            role='parent',
        )
        self.other_user = User.objects.create_user(
            username='other_parent',
            password='StrongTestPass123!',
            email='other@example.com',
            role='parent',
        )
        self.url = reverse('account_settings')

    def test_login_is_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_user_can_update_only_their_own_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'action': 'profile',
            'profile-first_name': 'New',
            'profile-last_name': 'Person',
            'profile-email': 'new@example.com',
            'profile-phone': '519-555-0123',
            'profile-current_password': 'StrongTestPass123!',
        })

        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.phone, '519-555-0123')
        self.assertEqual(self.other_user.email, 'other@example.com')

    def test_email_change_requires_current_password(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'action': 'profile',
            'profile-first_name': 'Old',
            'profile-last_name': 'Name',
            'profile-email': 'changed@example.com',
            'profile-phone': '',
            'profile-current_password': '',
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')

    def test_password_change_keeps_user_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'action': 'password',
            'password-old_password': 'StrongTestPass123!',
            'password-new_password1': 'NewStrongPass456!',
            'password-new_password2': 'NewStrongPass456!',
        })

        self.assertRedirects(response, self.url)
        self.assertIn('_auth_user_id', self.client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456!'))
