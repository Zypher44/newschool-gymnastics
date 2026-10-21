from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership
from .models import Video, VideoAnalysis
from .reference_examples import get_coaching_examples


class ReferenceExampleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user('example-owner', role='coach')
        self.other = User.objects.create_user('example-other', role='coach')
        self.athlete = User.objects.create_user('example-athlete', role='athlete')
        self.demonstrator = User.objects.create_user('example-demonstrator', role='athlete')
        self.gym = Gym.objects.create(name='Reference gym')
        for user in (self.owner, self.other, self.athlete, self.demonstrator):
            GymMembership.objects.create(gym=self.gym, user=user, role=user.role)
        self.video = self.create(title='My attempt', primary_athlete=self.athlete, is_coaching_example=False)
        self.example = self.create(title='Approved example', primary_athlete=self.demonstrator)

    def create(self, **overrides):
        marked = overrides.get('is_coaching_example', True)
        fields = dict(gym=self.gym, title='Example', event='bars', skill_name='Cast Handstand', video_file='video.mp4',
                      uploaded_by=self.owner, visibility='coaches', status='ready', is_coaching_example=True,
                      reference_marked_by=self.owner, reference_marked_at=timezone.now(), is_skill_library_video=marked,
                      skill_library_approved_by=self.owner if marked else None, skill_library_approved_at=timezone.now() if marked else None)
        fields.update(overrides)
        return Video.objects.create(**fields)

    def test_example_can_be_another_athlete_and_no_analysis_is_required(self):
        self.assertEqual(list(get_coaching_examples(self.video, self.owner)), [self.example])
        self.assertFalse(self.example.analyses.exists())
        self.client.force_login(self.owner)
        response = self.client.get(reverse('video_library:video_compare'), {'video_1': self.example.pk, 'video_2': self.video.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['first_video'].pk, self.example.pk)
        self.assertEqual(response.context['second_video'].pk, self.video.pk)
        self.assertIsNone(response.context['shared_athlete'])
        self.assertFalse(response.context['phase_comparisons'])

    def test_picker_excludes_unmarked_mismatched_unavailable_and_foreign_gym_examples(self):
        for fields in ({'skill_name': 'Back Tuck'}, {'event': 'floor'}, {'status': 'uploading'},
                       {'is_coaching_example': False}, {'skill_library_approved_by': None}, {'video_file': ''},
                       {'gym': Gym.objects.create(name='Foreign gym')}):
            self.create(**fields)
        self.assertEqual(list(get_coaching_examples(self.video, self.owner)), [self.example])

    def test_private_example_is_excluded_for_other_coaches(self):
        self.example.visibility = 'private'; self.example.save()
        self.assertFalse(get_coaching_examples(self.video, self.other).exists())
        self.assertTrue(get_coaching_examples(self.video, self.owner).exists())
        self.client.force_login(self.other)
        response = self.client.get(reverse('video_library:video_compare'), {'video_1': self.example.pk, 'video_2': self.video.pk})
        self.assertEqual(response.status_code, 404)

    def test_current_video_must_also_be_accessible(self):
        self.video.visibility = 'private'; self.video.save()
        self.assertFalse(get_coaching_examples(self.video, self.other).exists())
        self.assertFalse(get_coaching_examples(self.video, self.athlete).exists())

    def test_both_pages_render_example_first_and_attempt_second(self):
        analysis = VideoAnalysis.objects.create(video=self.video, status='completed')
        self.client.force_login(self.owner)
        for url in (reverse('video_library:video_detail', args=[self.video.pk]),
                    reverse('video_library:analysis_detail', args=[analysis.pk])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Compare with Coaching Example')
            self.assertContains(response, f'name="video_2" value="{self.video.pk}"')
            self.assertContains(response, f'<option value="{self.example.pk}">Approved example')

    def test_unmarking_removes_example_and_empty_state_explains_how_to_add_one(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('video_library:toggle_coaching_example', args=[self.example.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(get_coaching_examples(self.video, self.owner).exists())
        response = self.client.get(reverse('video_library:video_detail', args=[self.video.pk]))
        self.assertContains(response, 'No matching example is available.')
        self.assertContains(response, 'Approve as Skill Example')
