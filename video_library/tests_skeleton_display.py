from unittest.mock import patch
import re
from django.template.loader import render_to_string
from django.utils.html import escape
from django.test import TestCase
from django.urls import reverse
from .tests_keyframe_pictures import KeyframePictureTests
from .templatetags.video_pose_frames import picture_for


class SkeletonDisplayTests(TestCase):
    setUp = KeyframePictureTests.setUp
    create = KeyframePictureTests.create
    analysis = KeyframePictureTests.analysis
    frame = KeyframePictureTests.frame

    def test_saved_skeleton_is_default_on_video_and_analysis_pages_without_extra_flags(self):
        analysis = self.analysis(self.video)
        frame = self.frame(analysis,'athlete',2.25)
        frame.measurements.pop('pose_overlay_generated'); frame.measurements.pop('pose_detected'); frame.save()
        self.client.force_login(self.owner)
        for url in (reverse('video_library:video_detail',args=[self.video.pk]),reverse('video_library:analysis_detail',args=[analysis.pk])):
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertContains(response,f'src="{escape(frame.annotated_frame_image.url)}"')
            self.assertContains(response,'Skeleton Overlay')
            self.assertEqual(float(re.search(r'data-pose-frame-seek="([^"]+)"', response.content.decode()).group(1)), 2.25)
            self.assertContains(response,'Open Original Picture')
            self.assertNotContains(response,f'src="{escape(frame.frame_image.url)}"')

    def test_detection_failure_never_displays_an_old_skeleton(self):
        analysis=self.analysis(self.video)
        frame=self.frame(analysis,'athlete',2.25,pose_detected=False)
        self.assertFalse(picture_for(frame)['overlay'])
        self.client.force_login(self.owner)
        response=self.client.get(reverse('video_library:video_detail',args=[self.video.pk]))
        self.assertContains(response,f'src="{escape(frame.frame_image.url)}"')
        self.assertContains(response,'No athlete pose was detected')
        self.assertContains(response,'Generate Skeletons — Run Fresh Analysis')

    def test_missing_skeleton_offers_existing_background_analysis_action(self):
        analysis=self.analysis(self.video)
        frame=self.frame(analysis,'athlete',2.25)
        frame.annotated_frame_image='';frame.save()
        self.client.force_login(self.owner)
        response=self.client.get(reverse('video_library:analysis_detail',args=[analysis.pk]))
        self.assertContains(response,'Skeleton image is missing')
        self.assertContains(response,reverse('video_library:generate_pose_overlays',args=[self.video.pk]))
        response=self.client.post(reverse('video_library:generate_pose_overlays',args=[self.video.pk]))
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.video.analyses.filter(status='queued').count(),1)

    def test_legacy_widgets_default_to_skeleton_and_preserve_signed_image_urls(self):
        analysis=self.analysis(self.video)
        frame=self.frame(analysis,'athlete',2.25)
        context={'latest_analysis':analysis,'analysis_moment_items':[{'moment':frame,'feedback':None}]}
        with patch('django.core.files.storage.FileSystemStorage.url',side_effect=lambda name:f'https://media.example/{name}?signature=abc&expires=123'):
            for component in ('video_key_frames.html','video_timeline.html'):
                html=render_to_string('video_library/components/'+component,context)
                self.assertIn('athlete-overlay.jpg?signature=abc&amp;expires=123',html)
                self.assertNotIn('?v=',html)
                self.assertNotIn('&amp;v=',html)
                self.assertIn('Skeleton Overlay',html)

    def test_mock_cannot_supply_a_skeleton(self):
        analysis=self.analysis(self.video,analysis_source='mock')
        frame=self.frame(analysis,'mock',2.25)
        self.assertFalse(picture_for(frame)['overlay'])

    def test_comparison_picture_does_not_require_duplicate_generation_flag(self):
        first=self.frame(self.analysis(self.example),'example',2.25)
        second=self.frame(self.analysis(self.video),'attempt',5.75)
        for frame in (first,second):
            frame.measurements.pop('pose_overlay_generated');frame.save()
        self.client.force_login(self.owner)
        response=self.client.get(reverse('video_library:video_compare'),{'video_1':self.example.pk,'video_2':self.video.pk})
        self.assertContains(response,f'src="{escape(first.annotated_frame_image.url)}"')
        self.assertContains(response,f'src="{escape(second.annotated_frame_image.url)}"')
        self.assertNotContains(response,'pose overlay unavailable')
