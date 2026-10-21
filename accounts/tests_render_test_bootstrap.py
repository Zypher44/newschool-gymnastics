import io
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from gyms.models import GymMembership


class RenderTestBootstrapTests(TestCase):
    def run_bootstrap(self, **changes):
        config = SimpleNamespace(RENDER_TEST_ENVIRONMENT=True, DATABASES={
            'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'newschool_v2_test'}})
        for key, value in changes.items():
            setattr(config, key, value)
        output = io.StringIO()
        with patch('accounts.management.commands.bootstrap_render_test_admin.settings', config):
            call_command('bootstrap_render_test_admin', stdout=output)
        return output.getvalue()

    @patch.dict(os.environ, {'BOOTSTRAP_TEST_ADMIN_USERNAME': 'testdirector',
                             'BOOTSTRAP_TEST_ADMIN_PASSWORD': 'Local-test-fixture!4398'})
    def test_creates_director_with_active_gym_membership_and_hashed_password(self):
        message = self.run_bootstrap()
        user = get_user_model().objects.get(username='testdirector')
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertEqual(user.role, 'director')
        self.assertTrue(user.check_password('Local-test-fixture!4398'))
        self.assertTrue(GymMembership.objects.filter(user=user, role='director', is_active=True).exists())
        self.assertNotIn('Local-test-fixture', message)

    @patch.dict(os.environ, {'BOOTSTRAP_TEST_ADMIN_USERNAME': 'testdirector',
                             'BOOTSTRAP_TEST_ADMIN_PASSWORD': 'Local-test-fixture!4398'})
    def test_repeat_does_not_reset_password_or_duplicate_membership(self):
        self.run_bootstrap()
        user = get_user_model().objects.get(username='testdirector')
        password_hash = user.password
        with patch.dict(os.environ, {'BOOTSTRAP_TEST_ADMIN_PASSWORD': 'Changed-unused-fixture!3492'}):
            self.run_bootstrap()
        user.refresh_from_db()
        self.assertEqual(user.password, password_hash)
        self.assertEqual(GymMembership.objects.filter(user=user).count(), 1)

    @patch.dict(os.environ, {'BOOTSTRAP_TEST_ADMIN_USERNAME': 'taken',
                             'BOOTSTRAP_TEST_ADMIN_PASSWORD': 'Local-test-fixture!4398'})
    def test_existing_account_is_not_elevated(self):
        user = get_user_model().objects.create_user(username='taken', role='athlete')
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        user.refresh_from_db()
        self.assertEqual(user.role, 'athlete')
        self.assertFalse(user.is_superuser)

    def test_refuses_production_settings_and_database(self):
        with self.assertRaises(CommandError):
            self.run_bootstrap(RENDER_TEST_ENVIRONMENT=False)
        with self.assertRaises(CommandError):
            self.run_bootstrap(DATABASES={'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'production'}})

    @patch.dict(os.environ, {'BOOTSTRAP_TEST_ADMIN_USERNAME': 'testdirector',
                             'BOOTSTRAP_TEST_ADMIN_PASSWORD': 'weak'})
    def test_invalid_password_leaves_no_account(self):
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        self.assertFalse(get_user_model().objects.exists())
