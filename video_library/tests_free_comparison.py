from django.test import TestCase
from django.urls import reverse
from .models import VideoAnalysis, VideoAnalysisMoment
from .tests_reference_examples import ReferenceExampleTests


class FreeComparisonTests(TestCase):
    setUp = ReferenceExampleTests.setUp
    create = ReferenceExampleTests.create

    def compare(self):
        self.client.force_login(self.owner)
        return self.client.get(reverse('video_library:video_compare'), {'video_1':self.example.pk,'video_2':self.video.pk})

    def add_pose(self, video, timestamp):
        analysis = VideoAnalysis.objects.create(video=video,status='completed',analysis_source='pose',
            analysis_version='pose-evidence-1.0.0',raw_results={'camera_view':'side'})
        VideoAnalysisMoment.objects.create(analysis=analysis,timestamp_seconds=timestamp,label='Peak',frame_image='frame.jpg',
            measurements={'skill_phase':'peak','frame_quality_score':.8,'gymnastics_measurements':{
                'hip_position':{'average_angle':165}}})

    def test_no_analysis_still_provides_manual_alignment_and_speed_controls(self):
        response = self.compare()
        self.assertEqual(response.status_code,200)
        for label in ('Coach-marked Example','Athlete Attempt','Playback and Alignment','Use Current Positions as Review Point','¼ speed','Optional Pose Comparison Details'):
            self.assertContains(response,label)
        self.assertFalse(response.context['phase_comparisons'])
        self.assertNotContains(response,'AI Video Understanding')
        self.assertContains(response,'free-comparison.js')

    def test_phase_buttons_render_separate_times_for_each_clip(self):
        self.add_pose(self.example,2.25); self.add_pose(self.video,5.75)
        response = self.compare()
        self.assertContains(response,'Pose Review Points')
        self.assertContains(response,'data-first-time="2.25"')
        self.assertContains(response,'data-second-time="5.75"')
        self.assertNotContains(response,'const sharedTime')

    def test_different_skill_keeps_playback_but_hides_pose_differences(self):
        self.add_pose(self.example,2.25); self.add_pose(self.video,5.75)
        self.video.skill_name='Back Tuck'; self.video.save()
        response = self.compare()
        self.assertContains(response,'different or missing event/skill labels')
        self.assertContains(response,'Playback and Alignment')
        self.assertNotContains(response,'Pose Review Points')
        self.assertNotContains(response,'Largest Measurement Difference')
        self.assertNotContains(response,'Coach-marked Example')

    def test_private_example_and_foreign_gym_are_not_exposed(self):
        self.example.visibility='private'; self.example.save()
        self.client.force_login(self.other)
        response = self.client.get(reverse('video_library:video_compare'),{'video_1':self.example.pk,'video_2':self.video.pk})
        self.assertEqual(response.status_code,404)
        from gyms.models import Gym
        self.example.visibility='coaches'; self.example.gym=Gym.objects.create(name='Other gym'); self.example.save()
        self.assertEqual(self.compare().status_code,404)

    def test_titles_remain_escaped_and_unmarking_removes_reference_labels(self):
        self.example.title='<script>alert(1)</script>'; self.example.is_coaching_example=False; self.example.save()
        response = self.compare()
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertNotContains(response,'Coach-marked Example')
