from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from DjangoProject.render_test_media import DisabledTestMediaStorage


class DisabledTestStorageTests(SimpleTestCase):
    def test_upload_is_rejected_and_no_temporary_media_is_saved(self):
        storage = DisabledTestMediaStorage()
        with self.assertRaises(PermissionDenied):
            storage.save('videos/test.mp4', ContentFile(b'test video'))
        self.assertFalse(storage.exists('videos/test.mp4'))


@override_settings(RENDER_TEST_VIDEOS_ENABLED=False,
    MIDDLEWARE=[*settings.MIDDLEWARE, 'DjangoProject.render_test_media.TestMediaMiddleware'])
class CoreOnlyMediaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='core-test-head', role='head_coach')

    def setUp(self):
        self.client.force_login(self.user)

    def test_video_upload_page_explains_that_videos_are_paused(self):
        response = self.client.get(reverse('video_library:upload'))
        self.assertContains(response, 'Videos are paused for this test')

    def test_video_upload_post_is_rejected_before_view_saves_anything(self):
        from video_library.models import Video
        self.assertEqual(self.client.post(reverse('video_library:upload'), {}).status_code, 409)
        self.assertFalse(Video.objects.exists())

    def test_legacy_coach_upload_is_also_blocked(self):
        response = self.client.get(reverse('upload_athlete_video', args=[12345]))
        self.assertContains(response, 'Videos are paused for this test')

    def test_other_pages_are_still_accessible(self):
        self.assertEqual(self.client.get(reverse('account_settings')).status_code, 200)

    @override_settings(RENDER_TEST_VIDEOS_ENABLED=True)
    def test_video_mode_does_not_intercept_the_existing_view(self):
        response = self.client.get(reverse('upload_athlete_video', args=[12345]))
        self.assertTemplateUsed(response, 'coaches/not_allowed.html')
        self.assertNotContains(response, 'Videos are paused for this test')
