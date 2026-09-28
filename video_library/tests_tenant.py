from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from parents_portal.models import ParentAthleteLink
from practice_planner.models import TrainingGroup
from .forms import VideoUploadForm
from .models import Video, TechniqueProfile
from .views import get_accessible_videos


class VideoGymIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gym_a = Gym.objects.create(name='North')
        self.gym_b = Gym.objects.create(name='South')
        self.coach_a = User.objects.create_user('coach_a', password='pass', role='head_coach')
        self.coach_b = User.objects.create_user('coach_b', password='pass', role='head_coach')
        self.athlete_a = User.objects.create_user('athlete_a', password='pass', role='athlete')
        self.athlete_b = User.objects.create_user('athlete_b', password='pass', role='athlete')
        for gym, coach, athlete in ((self.gym_a, self.coach_a, self.athlete_a),
                                    (self.gym_b, self.coach_b, self.athlete_b)):
            GymMembership.objects.create(gym=gym, user=coach, role='head_coach')
            GymMembership.objects.create(gym=gym, user=athlete, role='athlete')
        self.video_b = Video.objects.create(
            gym=self.gym_b, title='South video', video_file='videos/south.mp4',
            primary_athlete=self.athlete_b, uploaded_by=self.coach_b,
        )
        self.video_a = Video.objects.create(
            gym=self.gym_a, title='North video', video_file='videos/north.mp4',
            primary_athlete=self.athlete_a, uploaded_by=self.coach_a,
        )

    def test_head_coach_cannot_open_another_gyms_video_by_id(self):
        self.client.force_login(self.coach_a)
        self.assertEqual(self.client.get(reverse(
            'video_library:video_detail', args=[self.video_b.pk])).status_code, 404)
        self.assertFalse(get_accessible_videos(self.coach_a).filter(pk=self.video_b.pk).exists())
        self.assertTrue(get_accessible_videos(self.coach_a).filter(pk=self.video_a.pk).exists())

    def test_upload_choices_exclude_another_gyms_athlete_and_group(self):
        group_b = TrainingGroup.objects.create(name='South group', gym=self.gym_b)
        form = VideoUploadForm(user=self.coach_a)
        self.assertNotIn(self.athlete_b, form.fields['primary_athlete'].queryset)
        self.assertNotIn(group_b, form.fields['training_group'].queryset)

    def test_unassigned_video_is_inaccessible(self):
        video = Video.objects.create(title='Unassigned', video_file='videos/old.mp4')
        self.assertFalse(get_accessible_videos(self.coach_a).filter(pk=video.pk).exists())

    def test_parent_cannot_open_video_from_childs_other_gym(self):
        parent = get_user_model().objects.create_user('parent_a', password='pass', role='parent')
        GymMembership.objects.create(gym=self.gym_a, user=parent, role='parent')
        GymMembership.objects.create(gym=self.gym_b, user=self.athlete_a, role='athlete')
        ParentAthleteLink.objects.create(parent=parent, athlete=self.athlete_a, approved=True)
        foreign_video = Video.objects.create(
            gym=self.gym_b, title='Other gym', video_file='videos/foreign.mp4',
            primary_athlete=self.athlete_a, uploaded_by=self.coach_b,
            visibility=Video.VISIBILITY_PARENTS,
        )
        self.client.force_login(parent)
        self.assertEqual(self.client.get(reverse('parent_video_detail', args=[foreign_video.pk])).status_code, 404)

    def test_head_coach_cannot_edit_foreign_technique_profile(self):
        profile = TechniqueProfile.objects.create(
            gym=self.gym_b, skill_name='Cast handstand', created_by=self.coach_b,
        )
        self.client.force_login(self.coach_a)
        self.assertEqual(self.client.get(reverse(
            'video_library:technique_profile_edit', args=[profile.pk])).status_code, 404)
