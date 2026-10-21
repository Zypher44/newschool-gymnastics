from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import Gym, GymMembership


class DirectorLoginHelpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gym = Gym.objects.create(name='Director test gym')
        cls.other_gym = Gym.objects.create(name='Other gym')
        cls.director = User.objects.create_user('help-director', role='director')
        GymMembership.objects.create(gym=cls.gym, user=cls.director, role='director')
        cls.people = []
        for role in ['head_coach', 'coach', 'athlete', 'parent']:
            user = User.objects.create_user('help-' + role, role=role, first_name='Test',
                                             password='Original-fixture-password!4789')
            member = GymMembership.objects.create(gym=cls.gym, user=user, role=role)
            cls.people.append(member)

    def setUp(self):
        self.client.force_login(self.director)
        self.member = self.people[2]
        self.url = reverse('reset_gym_person_password', args=[self.member.pk])
        self.new_password = 'New-unique-fixture-password!7948'

    def data(self):
        return {'new_password1': self.new_password, 'new_password2': self.new_password}

    def test_people_shows_usernames_and_reset_links_for_all_four_roles(self):
        page = self.client.get(reverse('people_management'))
        for member in self.people:
            self.assertContains(page, 'Username: <code>' + member.user.username + '</code>', html=True)
            self.assertContains(page, reverse('reset_gym_person_password', args=[member.pk]))

    def test_get_does_not_reveal_or_change_existing_password(self):
        before = self.member.user.password
        response = self.client.get(self.url)
        self.assertContains(response, self.member.user.username)
        self.assertNotContains(response, before)
        self.assertNotContains(response, 'Original-fixture-password!4789')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.member.user.refresh_from_db()
        self.assertEqual(self.member.user.password, before)

    def test_reset_works_for_each_member_role_and_records_no_password_in_audit(self):
        for member in self.people:
            response = self.client.post(reverse('reset_gym_person_password', args=[member.pk]), self.data())
            self.assertRedirects(response, reverse('people_management'))
            member.user.refresh_from_db()
            self.assertTrue(member.user.check_password(self.new_password))
            self.assertFalse(member.user.check_password('Original-fixture-password!4789'))
            audit = LogEntry.objects.get(object_id=str(member.user_id), user=self.director)
            self.assertNotIn(self.new_password, audit.change_message)

    def test_wrong_confirmation_and_weak_password_do_not_save_or_echo_password(self):
        for data in [dict(self.data(), new_password2='Different-fixture-password!7948'),
                     {'new_password1': '123', 'new_password2': '123'}]:
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertNotContains(response, 'value="' + data['new_password1'] + '"')
            self.member.user.refresh_from_db()
            self.assertTrue(self.member.user.check_password('Original-fixture-password!4789'))
        self.assertFalse(LogEntry.objects.exists())

    def test_other_gym_and_privileged_accounts_are_protected(self):
        User = get_user_model()
        outsider = User.objects.create_user('outside-coach', role='coach')
        foreign = GymMembership.objects.create(gym=self.other_gym, user=outsider, role='coach')
        self.assertEqual(self.client.post(reverse('reset_gym_person_password', args=[foreign.pk]), self.data()).status_code, 404)
        self.member.user.is_superuser = True
        self.member.user.save()
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)

    def test_non_directors_and_inactive_director_cannot_reset(self):
        for member in self.people:
            self.client.force_login(member.user)
            self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.client.force_login(self.director)
        GymMembership.objects.filter(user=self.director).update(is_active=False)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)

    def test_shared_account_cannot_be_reset_by_one_gym(self):
        GymMembership.objects.create(gym=self.other_gym, user=self.member.user, role='athlete')
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)

    def test_csrf_and_logged_out_access_are_protected(self):
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.director)
        self.assertEqual(secure.post(self.url, self.data()).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_old_target_session_is_invalidated_and_director_remains_signed_in(self):
        target = Client()
        self.assertTrue(target.login(username=self.member.user.username, password='Original-fixture-password!4789'))
        self.client.post(self.url, self.data())
        self.assertEqual(target.get(reverse('account_settings')).status_code, 302)
        self.assertEqual(self.client.get(reverse('people_management')).status_code, 200)

    def test_events_page_redirects_and_dashboard_uses_calendar(self):
        self.assertRedirects(self.client.get(reverse('director_event_list')), reverse('gym_calendar'))
        page = self.client.get(reverse('director_dashboard'))
        self.assertNotContains(page, 'href="' + reverse('director_event_list') + '"')
        self.assertContains(page, 'Open Calendar')
