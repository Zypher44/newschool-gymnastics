from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import AthletePathway, AthletePathwayRequirement, PathwayLevel, PathwayRequirement


class AthleteOverviewTests(TestCase):
    def setUp(self):
        self.athlete = get_user_model().objects.create_user(username='pathway-child', role='athlete')
        self.other = get_user_model().objects.create_user(username='private-child', role='athlete')
        self.client.force_login(self.athlete)
        self.url = reverse('pathway:pathway_overview')

    def test_own_current_target_progress_and_no_other_child_data(self):
        levels = list(PathwayLevel.objects.filter(is_active=True).order_by('order')[:2])
        plan = AthletePathway.objects.create(athlete=self.athlete, current_level=levels[0], target_level=levels[1])
        AthletePathway.objects.create(athlete=self.other, current_level=levels[1])
        for level in levels:
            req = PathwayRequirement.objects.filter(level=level, is_required=True, is_active=True).first()
            AthletePathwayRequirement.objects.create(athlete_pathway=plan, requirement=req, status='competition_ready', coach_note='PRIVATE_COACH_NOTE')
        before = list(AthletePathwayRequirement.objects.values())
        response = self.client.get(self.url, {'athlete_id': self.other.pk})
        self.assertEqual(response.status_code, 200)
        rows = response.context['parent_pathway_cards']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['athlete'], self.athlete)
        self.assertEqual(rows[0]['current_progress']['percentage'], 100)
        self.assertEqual(rows[0]['target_progress']['percentage'], 100)
        self.assertContains(response, 'Where I Am and Where I Can Go')
        self.assertContains(response, 'Athlete Pathway')
        self.assertNotContains(response, 'PRIVATE_COACH_NOTE')
        self.assertNotContains(response, 'private-child')
        self.assertNotContains(response, "View Child's Progress")
        self.assertEqual(before, list(AthletePathwayRequirement.objects.values()))

    def test_no_plan_has_friendly_empty_state_and_does_not_create_one(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Your coach has not set your pathway yet.')
        self.assertFalse(AthletePathway.objects.exists())
