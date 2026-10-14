from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership
from skill_tracker.models import Skill, Assignment
from skill_tracker.practice_targets import attach_practice_targets
from .models import EventSkillPlan
from .personal_models import AthletePracticePlan


class PersonalPlannerDeploymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gym = Gym.objects.create(name='Test Gym')
        cls.coach = User.objects.create_user(username='headtest', role='head_coach')
        cls.athlete = User.objects.create_user(username='childtest', role='athlete')
        cls.foreign = User.objects.create_user(username='foreignchild', role='athlete')
        for user in [cls.coach, cls.athlete]:
            GymMembership.objects.create(gym=cls.gym, user=user, role=user.role)
        other = Gym.objects.create(name='Other Gym')
        GymMembership.objects.create(gym=other, user=cls.foreign, role='athlete')
        cls.skill = Skill.objects.create(gym=cls.gym, event='beam', name='Cartwheel', key='cartwheel')

    def setUp(self):
        self.client.force_login(self.coach)
        self.url = reverse('practice_focus:planner')

    def data(self, action='save'):
        return {'athlete': self.athlete.pk, 'date': timezone.localdate().isoformat(),
                'title': 'Beam focus', 'action': action, 'skill_' + str(self.skill.pk): 'on',
                'target_' + str(self.skill.pk): '8', 'beam_minutes': '10'}

    def test_current_planner_displays_child_and_catalogue(self):
        response = self.client.get(self.url, {'athlete': self.athlete.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'practice_focus/personal_planner.html')
        self.assertContains(response, 'Cartwheel')

    def test_save_keeps_plan_individual_without_changing_current_skills(self):
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        plan = AthletePracticePlan.objects.get(athlete=self.athlete)
        self.assertEqual(plan.content['beam']['skills'][0]['target'], 8)
        self.assertFalse(EventSkillPlan.objects.exists())

    def test_publish_assigns_skill_and_attempt_target(self):
        data = self.data('publish')
        page = self.client.get(self.url, {'athlete': self.athlete.pk})
        data['current_version'] = page.context['form'].initial['current_version']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        plan = EventSkillPlan.objects.get(athlete=self.athlete, event='beam')
        self.assertEqual(plan.skill_names, ['Cartwheel'])
        assignments = attach_practice_targets(
            Assignment.objects.select_related('skill').filter(athlete=self.athlete, is_active=True),
            self.gym.pk, [self.athlete.pk], timezone.localdate())
        self.assertEqual(assignments[0].practice_target, 8)

    def test_foreign_athlete_is_blocked(self):
        data = self.data(); data['athlete'] = self.foreign.pk
        self.assertEqual(self.client.post(self.url, data).status_code, 404)
        self.assertFalse(AthletePracticePlan.objects.exists())

    def test_athlete_is_sent_to_own_plan(self):
        self.client.force_login(self.athlete)
        self.assertRedirects(self.client.get(self.url), reverse('practice_focus:my_plan'))
