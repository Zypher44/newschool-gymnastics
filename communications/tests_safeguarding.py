from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from coaches.models import CoachAthleteAssignment
from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from parents_portal.models import ParentAthleteLink
from practice_focus.passport_services import passport_metrics
from practice_focus.passport_models import PassportStamp
from surveys.models import DailySurvey
from .models import Conversation, ConversationParticipant, Message, Notification
from .services import create_or_get_conversation, get_allowed_message_recipients, send_message
from .safeguarding import can_view_conversation, supervision_error


class SupervisedCommunicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gym = Gym.objects.create(name='Sample Club')
        cls.other = Gym.objects.create(name='Other Club')
        User = get_user_model()
        for name, role in [('athlete', 'athlete'), ('coach', 'coach'), ('observer', 'coach'),
                           ('director', 'director'), ('parent', 'parent'), ('unlinked', 'parent')]:
            user = User.objects.create_user(username='safety_' + name, role=role, first_name=name.title())
            setattr(cls, name, user)
            GymMembership.objects.create(gym=cls.gym, user=user, role=role)
        cls.foreign = User.objects.create_user(username='foreign_observer', role='coach')
        GymMembership.objects.create(gym=cls.other, user=cls.foreign, role='coach')
        CoachAthleteAssignment.objects.create(coach=cls.coach, athlete=cls.athlete)
        cls.link = ParentAthleteLink.objects.create(parent=cls.parent, athlete=cls.athlete, approved=True)

    def supervised(self, observer=None):
        return create_or_get_conversation(creator=self.athlete, recipient=self.coach,
            observer=observer or self.parent, subject='Practice question')

    def test_role_matrix_blocks_athlete_director_and_keeps_parent_and_coach_routes(self):
        self.assertIn(self.coach, get_allowed_message_recipients(self.athlete))
        self.assertNotIn(self.director, get_allowed_message_recipients(self.athlete))
        self.assertNotIn(self.athlete, get_allowed_message_recipients(self.director))
        for user in [self.parent, self.coach]:
            self.assertIn(self.director, get_allowed_message_recipients(user))
            self.client.force_login(user)
            response = self.client.post(reverse('conversation_create'), {
                'recipient': self.director.pk, 'message': 'Question for director',
            })
            self.assertEqual(response.status_code, 302)
        for sender, recipient in [(self.athlete, self.director), (self.director, self.athlete)]:
            self.client.force_login(sender)
            response = self.client.post(reverse('conversation_create'), {
                'recipient': recipient.pk, 'observer': self.parent.pk, 'message': 'Blocked route',
            })
            self.assertEqual(response.status_code, 200)
            with self.assertRaises(PermissionError):
                create_or_get_conversation(creator=sender, recipient=recipient, observer=self.parent)
        self.assertFalse(Message.objects.filter(body='Blocked route').exists())

    def test_no_athlete_message_without_explicit_valid_observer(self):
        for observer in [None, self.unlinked, self.foreign, self.athlete, self.coach, self.director]:
            with self.subTest(observer=observer):
                with self.assertRaises(PermissionError):
                    create_or_get_conversation(creator=self.athlete, recipient=self.coach, observer=observer)
        self.assertFalse(Conversation.objects.exists())
        self.client.force_login(self.athlete)
        response = self.client.post(reverse('dashboard_message_send'), {
            'recipient': self.coach.pk, 'message': 'Please keep this draft',
        })
        self.assertContains(response, 'Please keep this draft')
        self.assertContains(response, 'explicitly selected')
        self.assertFalse(Message.objects.exists())

    @patch('django.core.mail.send_mail')
    def test_supervised_thread_has_exact_audience_and_shared_replies(self, mail):
        conversation = self.supervised()
        self.assertEqual(set(conversation.participants.values_list('pk', flat=True)),
            {self.athlete.pk, self.coach.pk, self.parent.pk})
        self.assertTrue(conversation.requires_supervision)
        self.assertEqual(conversation.related_athlete_id, self.athlete.pk)
        for sender in [self.athlete, self.coach, self.parent]:
            send_message(conversation=conversation, sender=sender, body='Routine skill question')
        self.assertEqual(conversation.messages.count(), 3)
        self.assertEqual(Notification.objects.filter(notification_type='message').count(), 6)
        self.assertEqual(self.supervised().pk, conversation.pk)
        mail.assert_not_called()
        self.client.force_login(self.athlete)
        response = self.client.get(conversation.get_absolute_url())
        self.assertContains(response, 'Visible to:')
        self.assertContains(response, 'Parent')
        self.assertNotContains(response, self.director.username)

    def test_second_coach_can_observe_without_copying_a_parent(self):
        conversation = self.supervised(self.observer)
        self.assertNotIn(self.parent, conversation.participants.all())
        self.assertIn(self.observer, conversation.participants.all())
        self.assertEqual(supervision_error(conversation), '')

    def test_old_one_to_one_thread_stays_private_and_read_only(self):
        old = Conversation.objects.create(gym=self.gym, created_by=self.athlete)
        old.participants.add(self.athlete, self.coach)
        Message.objects.create(conversation=old, sender=self.athlete, body='Earlier private history')
        self.client.force_login(self.athlete)
        response = self.client.post(old.get_absolute_url(), {'message': 'No new private reply'})
        self.assertContains(response, 'read-only')
        self.assertEqual(old.messages.count(), 1)
        new = self.supervised()
        self.assertNotEqual(new.pk, old.pk)
        self.assertFalse(old.participants.filter(pk=self.parent.pk).exists())
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(old.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(new.get_absolute_url()), 'Earlier private history')

    def test_revoked_parent_cannot_read_thread_or_notification_previews(self):
        conversation = self.supervised()
        send_message(conversation=conversation, sender=self.athlete, body='Sensitive sample text')
        ParentAthleteLink.objects.filter(pk=self.link.pk).update(approved=False)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(conversation.get_absolute_url()).status_code, 404)
        for route in ['communication_inbox', 'notification_list', 'parent_dashboard']:
            response = self.client.get(reverse(route))
            self.assertNotContains(response, 'Sensitive sample text')
        notice = Notification.objects.get(recipient=self.parent)
        self.assertEqual(self.client.get(reverse('notification_open', args=[notice.pk])).status_code, 404)
        with self.assertRaises(PermissionError):
            send_message(conversation=conversation, sender=self.coach, body='Must not send')
        self.assertEqual(conversation.messages.count(), 1)

    def test_inactive_observer_and_altered_participants_block_replies(self):
        conversation = self.supervised(self.observer)
        GymMembership.objects.filter(user=self.observer).update(is_active=False)
        with self.assertRaises(PermissionError):
            send_message(conversation=conversation, sender=self.athlete, body='Blocked')
        self.assertFalse(Message.objects.exists())

    def test_group_assignment_coach_is_available_without_direct_assignment(self):
        CoachAthleteAssignment.objects.all().delete()
        group = TrainingGroup.objects.create(gym=self.gym, name='Group')
        TrainingGroupAthlete.objects.create(group=group, athlete=self.athlete)
        TrainingGroupCoach.objects.create(group=group, coach=self.coach)
        self.assertIn(self.coach, get_allowed_message_recipients(self.athlete))
        self.assertIn(self.coach, get_allowed_message_recipients(self.parent))

    def test_csrf_and_foreign_accounts_cannot_send_or_read(self):
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.athlete)
        self.assertEqual(protected.post(reverse('conversation_create'), {
            'recipient': self.coach.pk, 'observer': self.parent.pk, 'message': 'Forged',
        }).status_code, 403)
        conversation = self.supervised()
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.get(conversation.get_absolute_url()).status_code, 404)
        self.assertFalse(Message.objects.exists())

    def test_full_composer_records_selected_observer_and_escapes_message(self):
        self.client.force_login(self.athlete)
        response = self.client.post(reverse('conversation_create'), {
            'recipient': self.coach.pk, 'observer': self.parent.pk, 'message': '<script>bad()</script>',
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.url)
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>bad()')
        self.assertTrue(Conversation.objects.get().requires_supervision)

    def test_practice_quests_do_not_reward_wellness_or_messages(self):
        today = timezone.localdate()
        before = passport_metrics(self.gym.pk, self.athlete.pk, today)
        DailySurvey.objects.create(athlete=self.athlete, survey_date=today, energy=1,
            checkin_version=2, body_feeling='pain')
        send_message(conversation=self.supervised(), sender=self.athlete, body='Skill question')
        self.assertEqual(passport_metrics(self.gym.pk, self.athlete.pk, today), before)
        self.assertFalse(PassportStamp.objects.exists())
        self.client.force_login(self.athlete)
        response = self.client.get(reverse('athlete_dashboard'))
        self.assertContains(response, 'Small quests. Your own progress.')
        self.assertNotContains(response, 'Day Streak')
        response = self.client.get(reverse('practice_focus:family_passport'))
        self.assertContains(response, 'Ask &amp; Learn')
        self.assertContains(response, 'Breaks do not reset your stamps.')
        self.assertFalse(PassportStamp.objects.exists())

    def test_support_is_accessible_without_login_and_does_not_send_reports(self):
        self.client.logout()
        response = self.client.get(reverse('safety_support'))
        self.assertContains(response, 'This page does not submit a report or alert anyone.')
        self.assertContains(response, 'https://sportintegrity.ca/report-safe-sport')
        self.assertNotContains(response, '<form')
        self.assertFalse(Conversation.objects.exists())
