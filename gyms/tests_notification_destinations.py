from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from athletes.models import AthleteProfile
from communications.models import Notification
from parents_portal.models import ParentAthleteLink
from .models import Gym, GymMembership


class ParentRequestNotificationTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Request gym')
        self.other = Gym.objects.create(name='Other request gym')
        self.director = self.person('director', 'director')
        self.parent = self.person('parent', 'parent')
        self.child = self.person('child', 'athlete')
        AthleteProfile.objects.create(user=self.child, date_of_birth=date(2015, 1, 2))
        self.url = reverse('parent_connection_requests')

    def person(self, name, role, gym=None):
        user = get_user_model().objects.create_user(name, role=role, first_name=name)
        GymMembership.objects.create(gym=gym or self.gym, user=user, role=role)
        return user

    def test_new_request_notification_opens_exact_request_without_approving(self):
        self.client.force_login(self.parent)
        self.client.post(reverse('connect_athlete'), {
            'athlete': self.child.pk, 'date_of_birth': '2015-01-02', 'relationship': 'Guardian',
        })
        link = ParentAthleteLink.objects.get(parent=self.parent, athlete=self.child)
        notification = Notification.objects.get(recipient=self.director)
        self.assertEqual(notification.link, self.url + f'#parent-request-{link.pk}')
        self.client.force_login(self.director)
        response = self.client.get(reverse('notification_open', args=[notification.pk]))
        self.assertRedirects(response, notification.link, fetch_redirect_response=False)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        response = self.client.get(self.url)
        self.assertContains(response, f'id="parent-request-{link.pk}"')
        self.assertContains(response, reverse('approve_parent_link', args=[link.pk]))
        link.refresh_from_db()
        self.assertFalse(link.approved)

    def test_existing_dashboard_and_blank_request_links_are_resolved_without_rewriting_history(self):
        self.client.force_login(self.director)
        for old_link in [reverse('director_dashboard'), '']:
            notification = Notification.objects.create(recipient=self.director,
                title='Parent connection request', link=old_link, notification_type='system')
            self.assertRedirects(self.client.get(reverse('notification_open', args=[notification.pk])), self.url)
            notification.refresh_from_db()
            self.assertEqual(notification.link, old_link)

    def test_other_destinations_are_preserved_and_notifications_remain_private(self):
        self.client.force_login(self.director)
        notification = Notification.objects.create(recipient=self.director, title='New message',
            notification_type='message', link=reverse('communication_inbox'))
        self.assertRedirects(self.client.get(reverse('notification_open', args=[notification.pk])),
                             notification.link, fetch_redirect_response=False)
        private = Notification.objects.create(recipient=self.parent, title='Private', link=self.url)
        self.assertEqual(self.client.get(reverse('notification_open', args=[private.pk])).status_code, 404)
        private.refresh_from_db()
        self.assertFalse(private.is_read)

    def test_queue_excludes_processed_inactive_and_other_gym_requests(self):
        pending = ParentAthleteLink.objects.create(parent=self.parent, athlete=self.child)
        other_parent = self.person('foreign-parent', 'parent', self.other)
        other_child = self.person('foreign-child', 'athlete', self.other)
        foreign = ParentAthleteLink.objects.create(parent=other_parent, athlete=other_child)
        self.client.force_login(self.director)
        page = self.client.get(self.url, {'gym': self.other.pk})
        self.assertContains(page, f'id="parent-request-{pending.pk}"')
        self.assertNotContains(page, f'id="parent-request-{foreign.pk}"')
        self.assertNotContains(page, 'foreign-parent')
        pending.approved = True
        pending.save()
        self.assertContains(self.client.get(self.url), 'No pending parent connections')
        pending.approved = False
        pending.save()
        GymMembership.objects.filter(user=self.parent).update(is_active=False)
        self.assertContains(self.client.get(self.url), 'No pending parent connections')

    def test_queue_is_director_only_and_read_only(self):
        for role in ['parent', 'athlete', 'coach', 'head_coach']:
            user = self.person('non-director-' + role, role)
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.director)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        GymMembership.objects.filter(user=self.director).update(is_active=False)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_approval_still_requires_explicit_post_and_csrf(self):
        pending = ParentAthleteLink.objects.create(parent=self.parent, athlete=self.child)
        self.client.force_login(self.director)
        action = reverse('approve_parent_link', args=[pending.pk])
        self.client.get(action)
        pending.refresh_from_db()
        self.assertFalse(pending.approved)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.director)
        self.assertEqual(secure.post(action).status_code, 403)
        self.client.post(action)
        pending.refresh_from_db()
        self.assertTrue(pending.approved)
        self.assertContains(self.client.get(self.url), 'No pending parent connections')
