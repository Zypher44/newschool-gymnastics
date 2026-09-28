from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from coaches.models import CoachAthleteAssignment
from parents_portal.models import ParentAthleteLink
from .dashboard import get_athlete_quick_message_options, get_parent_quick_message_options
from .services import get_allowed_message_recipients, users_may_message
from .models import Conversation, ConversationParticipant


class MessagingGymIsolationTests(TestCase):
    def test_quick_message_lists_hide_stale_cross_gym_links(self):
        User = get_user_model()
        north = Gym.objects.create(name='North')
        south = Gym.objects.create(name='South')
        athlete = User.objects.create_user('north_athlete', role='athlete')
        coach = User.objects.create_user('south_coach', role='coach')
        parent = User.objects.create_user('north_parent', role='parent')
        GymMembership.objects.create(gym=north, user=athlete, role='athlete')
        GymMembership.objects.create(gym=south, user=coach, role='coach')
        GymMembership.objects.create(gym=north, user=parent, role='parent')
        CoachAthleteAssignment.objects.create(coach=coach, athlete=athlete)
        self.assertNotIn(coach, get_athlete_quick_message_options(athlete))
        ParentAthleteLink.objects.create(parent=parent, athlete=athlete, approved=True)
        self.assertEqual(get_parent_quick_message_options(parent)[0]['coaches'].count(), 0)

        # An old approved link must not expose an athlete after a gym change.
        GymMembership.objects.filter(user=athlete, gym=north).update(gym=south)
        self.assertEqual(get_parent_quick_message_options(parent), [])

    def test_head_coach_cannot_message_another_gyms_parent(self):
        User = get_user_model()
        north = Gym.objects.create(name='North')
        south = Gym.objects.create(name='South')
        coach = User.objects.create_user('north_head', password='pass', role='head_coach')
        parent = User.objects.create_user('south_parent', password='pass', role='parent')
        GymMembership.objects.create(gym=north, user=coach, role='head_coach')
        GymMembership.objects.create(gym=south, user=parent, role='parent')
        self.assertNotIn(parent, get_allowed_message_recipients(coach))
        self.assertFalse(users_may_message(coach, parent))
        conversation = Conversation.objects.create(gym=south, created_by=parent)
        ConversationParticipant.objects.create(conversation=conversation, user=coach)
        ConversationParticipant.objects.create(conversation=conversation, user=parent)
        self.client.force_login(coach)
        self.assertEqual(self.client.get(reverse('conversation_detail', args=[conversation.pk])).status_code, 404)
