from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from athletes.models import AthleteProfile
from communications.models import Notification
from parents_portal.models import ParentAthleteLink
from pathway.models import PathwayLevel, PathwayRequirement

from .models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach


class GymRequestTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.north = Gym.objects.create(name='North')
        self.south = Gym.objects.create(name='South')
        self.director = User.objects.create_user('director_n', password='pass', role='director')
        self.other_director = User.objects.create_user('director_s', password='pass', role='director')
        for gym, user in [(self.north, self.director), (self.south, self.other_director)]:
            GymMembership.objects.create(gym=gym, user=user, role='director')

    def test_signup_notifies_only_the_chosen_director_and_shows_request(self):
        response = self.client.post(reverse('signup'), {
            'username': 'new_parent', 'first_name': 'New', 'last_name': 'Parent',
            'email': 'new_parent@example.com', 'password1': 'A-strong-passphrase-4871!',
            'password2': 'A-strong-passphrase-4871!',
            'role': 'parent', 'gym': self.north.pk,
        })
        self.assertEqual(response.status_code, 302)
        pending = GymMembership.objects.get(user__username='new_parent')
        self.assertFalse(pending.is_active)
        self.assertEqual(Notification.objects.filter(recipient=self.director).count(), 1)
        self.assertFalse(Notification.objects.filter(recipient=self.other_director).exists())
        self.client.force_login(self.director)
        dashboard = self.client.get(reverse('director_dashboard'))
        self.assertContains(dashboard, 'new member request')
        self.assertContains(dashboard, 'New Parent')
        self.client.post(reverse('toggle_gym_person_status', args=[pending.pk]))
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)
        self.assertTrue(Notification.objects.filter(recipient=pending.user,
                                                    title='Gym membership approved').exists())

    def test_parent_link_notifies_and_appears_only_at_matching_gym(self):
        User = get_user_model()
        parent = User.objects.create_user('parent_n', password='pass', role='parent')
        athlete = User.objects.create_user('athlete_n', password='pass', role='athlete',
                                           first_name='Alex', last_name='Test')
        for user, role in [(parent, 'parent'), (athlete, 'athlete')]:
            GymMembership.objects.create(gym=self.north, user=user, role=role)
        AthleteProfile.objects.create(user=athlete, date_of_birth=date(2015, 1, 2))
        self.client.force_login(parent)
        response = self.client.post(reverse('connect_athlete'), {
            'first_name': 'Alex', 'last_name': 'Test',
            'date_of_birth': '2015-01-02', 'relationship': 'Mother',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ParentAthleteLink.objects.filter(parent=parent, athlete=athlete,
                                                          approved=False).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.director,
                                                    title='Parent connection request').exists())
        self.client.force_login(self.director)
        self.assertContains(self.client.get(reverse('director_dashboard')), 'Alex Test')
        self.client.force_login(self.other_director)
        self.assertNotContains(self.client.get(reverse('director_dashboard')), 'Alex Test')

    def test_only_own_director_can_promote_a_coach(self):
        User = get_user_model()
        coach = User.objects.create_user('coach_n', password='pass', role='coach')
        membership = GymMembership.objects.create(gym=self.north, user=coach, role='coach')
        self.client.force_login(self.other_director)
        self.assertEqual(self.client.post(reverse('set_coach_role', args=[membership.pk])).status_code, 404)
        self.client.force_login(self.director)
        self.client.post(reverse('set_coach_role', args=[membership.pk]))
        membership.refresh_from_db()
        coach.refresh_from_db()
        self.assertEqual((membership.role, coach.role), ('head_coach', 'head_coach'))

    def test_coach_sees_only_assigned_athletes_in_pathway_manager(self):
        User = get_user_model()
        coach = User.objects.create_user('coach_n', password='pass', role='coach')
        GymMembership.objects.create(gym=self.north, user=coach, role='coach')
        assigned = User.objects.create_user('assigned_n', password='pass', role='athlete')
        unassigned = User.objects.create_user('unassigned_n', password='pass', role='athlete')
        other = User.objects.create_user('other_s', password='pass', role='athlete')
        for gym, user in [(self.north, assigned), (self.north, unassigned), (self.south, other)]:
            GymMembership.objects.create(gym=gym, user=user, role='athlete')
        group = TrainingGroup.objects.create(gym=self.north, name='Team')
        TrainingGroupCoach.objects.create(group=group, coach=coach, role='coach')
        TrainingGroupAthlete.objects.create(group=group, athlete=assigned)
        self.client.force_login(coach)
        manager = self.client.get(reverse('pathway:pathway_manager'))
        self.assertContains(manager, 'assigned_n')
        self.assertNotContains(manager, 'unassigned_n')
        self.assertNotContains(manager, 'other_s')
        search = self.client.get(reverse('athlete_search'))
        self.assertContains(search, 'Assigned Athletes')
        self.assertContains(search, 'Registered Athletes in Your Gym')
        self.assertContains(search, 'unassigned_n')
        self.assertNotContains(search, 'other_s')
        self.assertEqual(self.client.get(reverse('pathway:athlete_pathway_editor',
                                                     args=[unassigned.pk])).status_code, 404)

    def test_fresh_install_has_hp_catalogue(self):
        self.assertEqual(PathwayLevel.objects.filter(program='hp').count(), 4)
        self.assertEqual(PathwayRequirement.objects.filter(level__program='hp').count(), 82)
