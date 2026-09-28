from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from .models import PracticePlan, PracticeTemplate, TrainingGroup
from .views import get_accessible_groups, get_accessible_practices


class PracticeGymIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.north = Gym.objects.create(name='North')
        self.south = Gym.objects.create(name='South')
        self.coach_n = User.objects.create_user('coach_n', password='pass', role='head_coach')
        self.coach_s = User.objects.create_user('coach_s', password='pass', role='head_coach')
        GymMembership.objects.create(gym=self.north, user=self.coach_n, role='head_coach')
        GymMembership.objects.create(gym=self.south, user=self.coach_s, role='head_coach')
        self.group_s = TrainingGroup.objects.create(name='South group', gym=self.south)
        self.group_n = TrainingGroup.objects.create(name='North group', gym=self.north)
        self.practice_s = PracticePlan.objects.create(
            title='South practice', start_time=time(9), end_time=time(12),
            training_group=self.group_s, lead_coach=self.coach_s, created_by=self.coach_s,
        )
        self.template_s = PracticeTemplate.objects.create(
            name='South template', created_by=self.coach_s,
            gym=self.south, is_shared=True,
        )

    def test_head_coach_cannot_open_foreign_group_practice_or_shared_template(self):
        self.client.force_login(self.coach_n)
        for url in (
            reverse('practice_planner:training_group_detail', args=[self.group_s.pk]),
            reverse('practice_planner:practice_detail', args=[self.practice_s.pk]),
            reverse('practice_planner:practice_template_detail', args=[self.template_s.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertFalse(get_accessible_groups(self.coach_n).filter(pk=self.group_s.pk).exists())
        self.assertTrue(get_accessible_groups(self.coach_n).filter(pk=self.group_n.pk).exists())
        self.assertFalse(get_accessible_practices(self.coach_n).filter(pk=self.practice_s.pk).exists())
