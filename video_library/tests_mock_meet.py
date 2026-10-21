from django.test import SimpleTestCase

from .models import Video


class MockMeetVideoTypeTests(SimpleTestCase):
    def test_mock_meet_is_a_selectable_video_type(self):
        self.assertIn((Video.TYPE_MOCK_MEET, 'Mock Meet'), Video.VIDEO_TYPE_CHOICES)
