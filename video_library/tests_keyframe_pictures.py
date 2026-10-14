from django.test import TestCase
from django.urls import reverse
from .models import VideoAnalysis, VideoAnalysisMoment
from .tests_reference_examples import ReferenceExampleTests


class KeyframePictureTests(TestCase):
    setUp = ReferenceExampleTests.setUp
    create = ReferenceExampleTests.create

    def compare(self):
        self.client.force_login(self.owner)
        return self.client.get(reverse('video_library:video_compare'), {'video_1':self.example.pk,'video_2':self.video.pk})

    def analysis(self, video, **overrides):
        values = {'video':video,'status':'completed','analysis_source':'pose','analysis_version':'pose-evidence-1.0.0',
                  'raw_results':{'camera_view':'side'}}
        values.update(overrides)
        return VideoAnalysis.objects.create(**values)

    def frame(self, analysis, name, timestamp, **overrides):
        measurements = {'skill_phase':'peak','is_key_frame':True,'frame_quality_score':.8,
                        'pose_detected':True,'pose_overlay_generated':True,
                        'gymnastics_measurements':{'hip_position':{'average_angle':165}}}
        measurements.update(overrides)
        return VideoAnalysisMoment.objects.create(analysis=analysis,timestamp_seconds=timestamp,label='Peak',
            frame_image=f'{name}-original.jpg',annotated_frame_image=f'{name}-overlay.jpg',measurements=measurements)

    def test_pictures_are_exact_frames_selected_for_phase_measurements(self):
        first = self.analysis(self.example)
        self.frame(first,'a-lower-quality',1.25,frame_quality_score=.6)
        chosen = self.frame(first,'a-chosen',2.25,frame_quality_score=.9)
        second = self.frame(self.analysis(self.video),'b-chosen',5.75)
        response = self.compare()
        self.assertEqual(response.status_code,200)
        phase = response.context['keyframe_comparisons'][0]
        self.assertEqual(phase['first']['frame_moment'].pk,chosen.pk)
        self.assertEqual(phase['second']['frame_moment'].pk,second.pk)
        for image in ('a-chosen-overlay.jpg','b-chosen-overlay.jpg'):
            self.assertContains(response,image)
        for image in ('a-lower-quality-overlay.jpg','a-chosen-original.jpg','b-chosen-original.jpg'):
            self.assertNotContains(response,image)
        self.assertContains(response,'data-first-time="2.25"')
        self.assertContains(response,'data-second-time="5.75"')
        self.assertContains(response,'Open Full-size Pose Picture')
        self.assertContains(response,'Key Frame Pictures')

    def test_overlay_missing_or_pose_not_detected_uses_labeled_original(self):
        frame = self.frame(self.analysis(self.example),'a',2.25)
        frame.annotated_frame_image=''; frame.save()
        self.frame(self.analysis(self.video),'b',5.75,pose_detected=False)
        response = self.compare()
        self.assertContains(response,'a-original.jpg')
        self.assertContains(response,'b-original.jpg')
        self.assertNotContains(response,'b-overlay.jpg')
        self.assertContains(response,'Original frame — pose overlay unavailable')
        self.assertContains(response,'Open Full-size Original Frame')

    def test_no_analysis_or_unpaired_phase_has_clear_empty_state(self):
        self.assertContains(self.compare(),'No paired key frame pictures are available yet')
        self.frame(self.analysis(self.example),'a',2.25)
        response = self.compare()
        self.assertContains(response,'No paired key frame pictures are available yet')
        self.assertNotContains(response,'a-overlay.jpg')

    def test_missing_source_frame_is_not_used_as_a_picture(self):
        self.frame(self.analysis(self.example),'a',2.25)
        frame = self.frame(self.analysis(self.video),'b',5.75)
        frame.frame_image=None; frame.save()
        response = self.compare()
        self.assertFalse(response.context['keyframe_comparisons'])
        self.assertNotContains(response,'b-overlay.jpg')

    def test_legacy_mock_front_view_and_mismatched_skill_do_not_supply_pictures(self):
        self.frame(self.analysis(self.example),'a',2.25)
        for options in ({'analysis_source':'mock'}, {'analysis_version':'old'}, {'raw_results':{'camera_view':'front'}}):
            analysis = self.analysis(self.video,**options)
            self.frame(analysis,'ineligible',5.75)
            response = self.compare()
            self.assertNotContains(response,'ineligible-overlay.jpg')
            analysis.delete()
        self.frame(self.analysis(self.video),'b',5.75)
        self.video.skill_name='Back Tuck'; self.video.save()
        response = self.compare()
        self.assertNotContains(response,'Key Frame Pictures')
        self.assertNotContains(response,'a-overlay.jpg')
        self.assertNotContains(response,'b-overlay.jpg')

    def test_private_or_foreign_video_pictures_remain_inaccessible(self):
        self.frame(self.analysis(self.example),'private',2.25)
        self.frame(self.analysis(self.video),'attempt',5.75)
        self.example.visibility='private'; self.example.save()
        self.client.force_login(self.other)
        url=reverse('video_library:video_compare')
        response=self.client.get(url,{'video_1':self.example.pk,'video_2':self.video.pk})
        self.assertEqual(response.status_code,404)
        self.assertNotContains(response,'private-overlay.jpg',status_code=404)

    def test_picture_labels_escape_user_titles(self):
        self.example.is_coaching_example=False; self.example.title='<script>bad()</script>'; self.example.save()
        self.frame(self.analysis(self.example),'a',2.25)
        self.frame(self.analysis(self.video),'b',5.75)
        response=self.compare()
        self.assertContains(response,'&lt;script&gt;bad()&lt;/script&gt;')
        self.assertNotContains(response,'<script>bad()</script>')
