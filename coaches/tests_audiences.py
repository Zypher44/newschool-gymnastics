from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from communications.models import Conversation, Message, Notification
from communications.services import get_allowed_message_recipients
from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupCoach, TrainingGroupAthlete
from parents_portal.models import ParentAthleteLink
from .audiences import visible_events
from .models import CoachAthleteAssignment, TeamEvent


class GymAudienceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gym = Gym.objects.create(name='Home Gym')
        self.other = Gym.objects.create(name='Other Gym')
        self.people = {}
        for name, role, gym in [
            ('director_test', 'director', self.gym),
            ('coach_test', 'coach', self.gym),
            ('coach_other_group', 'coach', self.gym),
            ('parent_test', 'parent', self.gym),
            ('athlete_test', 'athlete', self.gym),
            ('external_director', 'director', self.other),
            ('external_parent', 'parent', self.other),
        ]:
            user = User.objects.create_user(name, password='pass', role=role)
            GymMembership.objects.create(gym=gym, user=user, role=role)
            self.people[name] = user
        self.group = TrainingGroup.objects.create(gym=self.gym, name='Stars')
        self.other_group = TrainingGroup.objects.create(gym=self.gym, name='Moon')
        TrainingGroupCoach.objects.create(group=self.group, coach=self.people['coach_test'])
        TrainingGroupCoach.objects.create(group=self.other_group, coach=self.people['coach_other_group'])
        TrainingGroupAthlete.objects.create(group=self.group, athlete=self.people['athlete_test'])
        ParentAthleteLink.objects.create(parent=self.people['parent_test'], athlete=self.people['athlete_test'], approved=True)
        CoachAthleteAssignment.objects.create(coach=self.people['coach_test'], athlete=self.people['athlete_test'])

    def test_dashboard_message_choices_and_parent_coach_message(self):
        director = self.people['director_test']
        coach = self.people['coach_test']
        parent = self.people['parent_test']

        self.client.force_login(coach)
        response = self.client.get(reverse('coach_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{director.pk}"')
        self.assertContains(response, 'Choose a director, athlete or parent')
        self.assertEqual(response.content.count(b'id="communication-recipient"'), 1)

        self.client.force_login(parent)
        response = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{director.pk}"')
        self.assertContains(response, f'value="{coach.pk}"')
        for recipient in (coach, director):
            response = self.client.post(reverse('dashboard_message_send'), {
                'recipient': recipient.pk, 'message': f'Hello {recipient.username}',
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Message.objects.filter(sender=parent, body=f'Hello {recipient.username}').exists())

        response = self.client.post(reverse('dashboard_message_send'), {
            'recipient': self.people['external_director'].pk, 'message': 'Wrong gym',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Message.objects.filter(body='Wrong gym').exists())

    def test_parent_and_coach_can_message_director_in_same_gym(self):
        director = self.people['director_test']
        for name in ('coach_test', 'parent_test'):
            sender = self.people[name]
            self.assertIn(director, get_allowed_message_recipients(sender))
            self.assertNotIn(self.people['external_director'], get_allowed_message_recipients(sender))
            self.client.force_login(sender)
            response = self.client.post(reverse('conversation_create'), {
                'recipient': director.pk, 'subject': 'Question', 'message': 'Hello director',
            })
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.filter(body='Hello director').count(), 2)

    def test_coach_group_announcement_cannot_include_other_group_or_gym(self):
        self.client.force_login(self.people['coach_test'])
        response = self.client.post(reverse('gym_announcement'), {
            'audience': 'group', 'training_group': self.group.pk, 'message': 'Practice tomorrow',
        })
        self.assertRedirects(response, reverse('communication_inbox'))
        recipients = set(Conversation.objects.values_list('participants__username', flat=True))
        self.assertEqual(recipients, {'coach_test', 'athlete_test', 'parent_test'})
        count = Message.objects.count()
        response = self.client.post(reverse('gym_announcement'), {
            'audience': 'group', 'training_group': self.other_group.pk, 'message': 'Bad group',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.count(), count)
        response = self.client.post(reverse('gym_announcement'), {
            'audience': 'group', 'training_group': 'bogus', 'message': 'Bad ID',
        })
        self.assertEqual(response.status_code, 200)

    def test_event_audience_and_calendar_visibility(self):
        director = self.people['director_test']
        self.client.force_login(director)
        response = self.client.post(reverse('add_event'), {
            'title': 'Stars practice', 'event_date': '2026-10-10',
            'audience': 'group', 'training_group': self.group.pk,
        })
        self.assertEqual(response.status_code, 302)
        event = TeamEvent.objects.get(title='Stars practice')
        self.assertEqual(event.training_group, self.group)
        for name in ('athlete_test', 'parent_test', 'coach_test'):
            user = self.people[name]
            self.assertIn(event, visible_events(user))
            self.client.force_login(user)
            response = self.client.get(reverse('gym_calendar') + '?month=2026-10')
            self.assertContains(response, 'Stars practice')
        for name in ('coach_other_group', 'external_parent'):
            user = self.people[name]
            self.assertNotIn(event, visible_events(user))
            self.client.force_login(user)
            response = self.client.get(reverse('gym_calendar') + '?month=2026-10')
            self.assertNotContains(response, 'Stars practice')
            self.assertFalse(Notification.objects.filter(recipient=user, title='New Event: Stars practice').exists())

    def test_coach_routine_tracker_page_loads(self):
        self.client.force_login(self.people['coach_test'])
        response = self.client.get(reverse('routine_tracker:daily_routine_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'athlete_test')

    def test_calendar_sidebar_and_account_menu_placement(self):
        for name, section, following in (
            ('director_test', 'Gym Management', 'Gym Events'),
            ('coach_test', 'Planning', 'Pathway Manager'),
            ('parent_test', 'Communication', 'Notifications'),
        ):
            self.client.force_login(self.people[name])
            response = self.client.get(reverse('gym_calendar'))
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            sidebar = html.split('<div class="sidebar-navigation">', 1)[1].split('<div class="sidebar-account">', 1)[0]
            self.assertEqual(sidebar.count('href="/calendar/"'), 1)
            self.assertLess(sidebar.index(section), sidebar.index('href="/calendar/"'))
            self.assertLess(sidebar.index('href="/calendar/"'), sidebar.index(following))
            self.assertIn('href="/calendar/" class="dropdown-item">📅 Calendar', html)
