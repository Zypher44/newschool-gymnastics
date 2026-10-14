"""Coach guide content, saved progress, and role boundaries."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership
from practice_hub.models import OnboardingProgress


class CoachWalkthroughTests(TestCase):
    old_keys = ['group', 'plan', 'track', 'review', 'ready']
    keys = ['group', 'plan', 'track', 'review', 'reports', 'passport',
            'videos', 'video-feedback', 'ready']

    def setUp(self):
        self.gym = Gym.objects.create(name='Walkthrough Gym')
        self.head = self.person('head', 'head_coach')
        self.client.force_login(self.head)
        self.url = reverse('practice_hub:onboarding')

    def person(self, name, role):
        user = get_user_model().objects.create_user(username=name, role=role)
        GymMembership.objects.create(user=user, gym=self.gym, role=role)
        return user

    def progress(self, **overrides):
        return OnboardingProgress.objects.create(user=self.head, gym=self.gym,
            role='head_coach', **overrides)

    def post_step(self, step, version, action='next', **extra):
        return self.client.post(self.url, {'step': step, 'version': version,
            'action': action, 'acknowledge': 'yes', **extra})

    def test_both_coach_roles_have_new_lessons_and_working_destinations(self):
        for user in (self.head, self.person('coach', 'coach')):
            self.client.force_login(user)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            steps = response.context['steps']
            self.assertEqual([step['key'] for step in steps], self.keys)
            self.assertEqual([step['key'] for step in steps if step['new']],
                ['reports', 'passport', 'videos', 'video-feedback'])
            for step in steps:
                for link in step['links']:
                    self.assertTrue(link['url'], link['label'])
            self.assertFalse(OnboardingProgress.objects.filter(user=user).exists())

    def test_badge_lesson_explains_attendance_effort_and_personal_progress(self):
        response = self.client.get(self.url, {'step': 5})
        for text in ('Why gamify practice?', 'Practice Pal', 'Present and Late',
                     'Planned breaks do not reset', 'Correction Detective',
                     'Great Teammate', 'Better Than Before', 'age-appropriate',
                     'approved linked parents', 'Previously earned stamps',
                     'Ask athletes which goals', 'skill mastery'):
            self.assertContains(response, text)
        self.assertContains(response, reverse('practice_focus:coach_passport'))
        self.assertContains(response, reverse('practice_focus:badge_editor'))

    def test_every_lesson_renders_without_creating_live_practice_records(self):
        from practice_focus.models import TrackedResult, PassportStamp
        from skill_tracker.models import SkillResult
        from practice_hub.models import PracticeSession
        models = (TrackedResult, PassportStamp, SkillResult, PracticeSession)
        before = [model.objects.count() for model in models]
        for index in range(len(self.keys)):
            response = self.client.get(self.url, {'step': index})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['step']['key'], self.keys[index])
        self.assertEqual(before, [model.objects.count() for model in models])
        self.assertFalse(OnboardingProgress.objects.exists())

    def test_previously_completed_guide_opens_first_new_lesson_read_only(self):
        progress = self.progress(completed_steps=self.old_keys, current_step=4,
            completed_at=timezone.now(), version=7)
        before = OnboardingProgress.objects.values().get(pk=progress.pk)
        response = self.client.get(self.url)
        self.assertEqual(response.context['step']['key'], 'reports')
        self.assertEqual(response.context['completed_count'], 5)
        self.assertEqual(response.context['new_lesson_count'], 4)
        self.assertTrue(response.context['guide_updated'])
        self.assertFalse(response.context['guide_complete'])
        self.assertContains(response, 'Your reviewed steps are saved.')
        self.assertEqual(before, OnboardingProgress.objects.values().get(pk=progress.pk))

    def test_old_reviews_survive_and_completion_requires_all_new_lessons(self):
        progress = self.progress(completed_steps=self.old_keys, current_step=4,
            completed_at=timezone.now(), version=7)
        self.post_step(4, 7)
        progress.refresh_from_db()
        self.assertIsNone(progress.completed_at)
        self.assertTrue(set(self.old_keys).issubset(progress.completed_steps))
        self.assertIn('reports', progress.completed_steps)
        self.post_step(8, 8, 'finish')
        progress.refresh_from_db()
        self.assertIsNone(progress.completed_at)
        self.assertEqual(progress.version, 8)
        for index, version in ((5, 8), (6, 9), (7, 10)):
            self.post_step(index, version)
        self.post_step(8, 11, 'finish')
        progress.refresh_from_db()
        self.assertIsNotNone(progress.completed_at)
        self.assertEqual(progress.completed_steps, self.keys)
        self.assertTrue(self.client.get(self.url).context['guide_complete'])

    def test_partial_guide_keeps_place_and_unknown_keys_do_not_inflate_count(self):
        progress = self.progress(completed_steps=['group', 'plan', 'retired'], current_step=2)
        response = self.client.get(self.url)
        self.assertEqual(response.context['step']['key'], 'track')
        self.assertEqual(response.context['completed_count'], 2)
        progress.refresh_from_db()
        self.assertEqual(progress.completed_steps, ['group', 'plan', 'retired'])

    def test_stale_tab_cannot_overwrite_new_reviews(self):
        progress = self.progress(completed_steps=self.old_keys, completed_at=timezone.now(), version=7)
        self.post_step(4, 7)
        before = OnboardingProgress.objects.values().get(pk=progress.pk)
        self.post_step(5, 7)
        self.assertEqual(before, OnboardingProgress.objects.values().get(pk=progress.pk))

    def test_progress_stays_with_signed_in_person(self):
        other = self.person('other', 'coach')
        self.post_step(0, 0, user=other.pk, gym=999, role='coach')
        progress = OnboardingProgress.objects.get()
        self.assertEqual(progress.user, self.head)
        self.assertEqual(progress.gym, self.gym)
        self.assertEqual(progress.role, 'head_coach')

    def test_other_roles_keep_their_existing_guides(self):
        expected = {'director': ['gym', 'people', 'groups', 'practice', 'ready'],
                    'athlete': ['plan', 'track', 'progress', 'ready'],
                    'parent': ['connect', 'progress', 'feedback', 'ready']}
        for role, keys in expected.items():
            user = self.person(role, role)
            self.client.force_login(user)
            response = self.client.get(self.url)
            self.assertEqual([step['key'] for step in response.context['steps']], keys)
            self.assertNotContains(response, 'Why gamify practice?')
            self.assertFalse(OnboardingProgress.objects.filter(user=user).exists())
