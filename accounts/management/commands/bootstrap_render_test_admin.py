"""Create the first test director from environment variables; never reset users."""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Create an initial director only in the isolated Render test database.'

    def handle(self, *args, **options):
        if not getattr(settings, 'RENDER_TEST_ENVIRONMENT', False):
            raise CommandError('This command is restricted to the Render test settings.')
        database = settings.DATABASES['default']
        if database['ENGINE'] != 'django.db.backends.postgresql' or database['NAME'] != 'newschool_v2_test':
            raise CommandError('Refusing bootstrap outside the separate test PostgreSQL database.')
        username = os.environ.get('BOOTSTRAP_TEST_ADMIN_USERNAME', '').strip()
        password = os.environ.get('BOOTSTRAP_TEST_ADMIN_PASSWORD', '')
        if not username and not password:
            self.stdout.write('Test account bootstrap not configured; skipped.')
            return
        if not username or not password:
            raise CommandError('Set both BOOTSTRAP_TEST_ADMIN_USERNAME and BOOTSTRAP_TEST_ADMIN_PASSWORD.')
        User = get_user_model()
        with transaction.atomic():
            existing = User.objects.filter(username=username).first()
            if existing:
                if existing.is_staff and existing.is_superuser and existing.role == 'director':
                    self.stdout.write('Test director already exists; password and membership unchanged.')
                    return
                raise CommandError('The bootstrap username belongs to another account; choose a new username.')
            candidate = User(username=username, role='director', is_staff=True, is_superuser=True)
            try:
                candidate.full_clean(exclude=['password'])
                validate_password(password, candidate)
                if len(password) < 12:
                    raise ValidationError('Use a test password of at least 12 characters.')
            except ValidationError:
                raise CommandError('Invalid test username or weak password. Use a valid username and a strong password of at least 12 characters.') from None
            user = User.objects.create_superuser(username=username, password=password, role='director')
            from gyms.models import Gym, GymMembership
            gym = Gym.objects.create(name='NewSchool V2 Test Gym')
            GymMembership.objects.create(gym=gym, user=user, role='director', is_active=True)
        self.stdout.write(self.style.SUCCESS('Initial test director and test gym created.'))
