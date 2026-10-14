import copy
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import translation
from .tests_keyframe_pictures import KeyframePictureTests
from .ai.aligned_timing import aligned_timing
from .ai.comparison_summary import build_comparison_summary
from .ai.comparison_insights import build_comparison_insights


class AlignedTimingTests(SimpleTestCase):
    def phases(self, offset=0):
        return [{'name': name, 'label': name.title(), 'first': {'timestamp': a}, 'second': {'timestamp': b + offset}}
                for name, a, b in [('entry', 1, 4), ('peak', 3, 6), ('finish', 5, 9)]]

    def test_extra_footage_does_not_become_a_technique_timing_difference(self):
        original = copy.deepcopy(self.phases())
        result = build_comparison_summary(original)
        rows = {row['phase']: row for row in result['timing_changes']}
        self.assertEqual(rows['peak']['delta'], 0)
        self.assertEqual(rows['finish']['delta'], 1)
        self.assertEqual(rows['peak']['first'], 2)
        shifted = {row['phase']: row for row in build_comparison_summary(self.phases(100))['timing_changes']}
        self.assertEqual(shifted['finish']['delta'], rows['finish']['delta'])
        self.assertEqual(original, self.phases())

    def test_missing_entry_has_no_timing_claim(self):
        self.assertFalse(aligned_timing(self.phases()[1:])['rows'])
        self.assertIsNone(build_comparison_summary(self.phases()[1:])['largest_timing_change'])

    def test_invalid_or_reversed_phase_times_are_not_compared(self):
        for value in ('NaN', 'inf', -1, True, 0.5, 1):
            phases = self.phases(); phases[1]['first']['timestamp'] = value
            self.assertFalse(aligned_timing(phases)['rows'], value)


class ComparisonInsightTests(TestCase):
    setUp = KeyframePictureTests.setUp
    create = KeyframePictureTests.create

    def analysis(self, video):
        return KeyframePictureTests.analysis(self, video, requested_skill=video.skill_name,
                                             raw_results={'camera_view': 'side', 'selected_skill': video.skill_name})

    def frame(self, analysis, phase, time, bend=0):
        landmarks = {'left_shoulder': {'x': .4, 'y': .2, 'visibility': .95},
                     'left_hip': {'x': .4, 'y': .4, 'visibility': .95},
                     'left_knee': {'x': .4, 'y': .6, 'visibility': .95},
                     'left_ankle': {'x': .4 + bend, 'y': .8, 'visibility': .95},
                     'left_elbow': {'x': .4, 'y': .1, 'visibility': .95},
                     'left_wrist': {'x': .4, 'y': 0, 'visibility': .95}}
        return KeyframePictureTests.frame(self, analysis, f'{analysis.pk}-{phase}', time, skill_phase=phase,
                skill_phase_confidence=.85, pose_landmarks=landmarks, image_width=800, image_height=400,
                measurement_space='image_plane_height_units_v2',
                gymnastics_measurements={'average_landmark_visibility': .95, 'knee_extension': {'average_angle': 180}})

    def pair(self):
        self.a, self.b = self.analysis(self.example), self.analysis(self.video)
        self.frames_a = [self.frame(self.a, 'entry', 1), self.frame(self.a, 'peak', 3)]
        self.frames_b = [self.frame(self.b, 'entry', 4), self.frame(self.b, 'peak', 6, .1)]
        self.phases = [{'name': name, 'label': name.title(),
                        'first': {'frame_moment': a, 'timestamp': float(a.timestamp_seconds)},
                        'second': {'frame_moment': b, 'timestamp': float(b.timestamp_seconds)}}
                       for name, a, b in zip(('entry', 'peak'), self.frames_a, self.frames_b)]

    def insights(self, **options):
        return build_comparison_insights(self.phases, self.example, self.video, self.a, self.b,
                                        matching=options.get('matching', True), example=options.get('example', True))

    def test_highlight_uses_exact_visible_joint_with_correct_aspect_ratio(self):
        self.pair(); result = self.insights(); item = result['focus']
        self.assertEqual(item['label'], 'Left knee')
        self.assertEqual(item['first']['angle'], 180)
        self.assertAlmostEqual(item['second']['angle'], 135)
        self.assertAlmostEqual(item['gap'], 45)
        self.assertEqual(item['second']['vertex'], {'x': 320, 'y': 240})
        self.assertEqual(item['second']['width'], 800)
        self.assertEqual(item['second_time'], 6)
        self.assertEqual(result['timing']['rows'][0]['delta'], 0)
        self.assertEqual(result['strength']['gap'], 0)

    def test_one_focus_draft_and_page_do_not_save_without_coach_action(self):
        self.pair(); self.client.force_login(self.owner)
        with translation.override('fr'):
            response = self.client.get(reverse('video_library:video_compare'), {'video_1': self.example.pk, 'video_2': self.video.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'One Focus for the Next Turn')
        self.assertContains(response, 'keyframe-highlight-overlay')
        self.assertContains(response, 'viewBox="0 0 800.0 400.0"')
        self.assertContains(response, 'value="1.0"')
        self.assertContains(response, 'value="4.0"')
        self.assertContains(response, reverse('video_library:review_analysis', args=[self.b.pk]))
        self.assertNotContains(response, 'Largest Timing Difference')
        self.b.refresh_from_db(); self.assertEqual(self.b.coach_review_notes, '')
        self.assertIsNone(self.b.reviewed_by)
        result = self.client.post(reverse('video_library:review_analysis', args=[self.b.pk]),
                                 {'review_status': 'partial', 'coach_review_notes': 'Coach chose knee shape.'})
        self.assertEqual(result.status_code, 302)
        self.b.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(self.b.coach_review_notes, 'Coach chose knee shape.')
        self.assertEqual(self.a.coach_review_notes, '')

    def test_occluded_joint_and_presence_do_not_make_a_focus(self):
        self.pair()
        for visibility, presence in [(0.3, None), (.95, .2), ('NaN', None), (.95, 'inf')]:
            self.frames_b[1].measurements['pose_landmarks']['left_ankle'].update(visibility=visibility, presence=presence)
            self.assertIsNone(self.insights()['focus'])

    def test_malformed_dimensions_landmarks_and_phase_confidence_are_rejected(self):
        self.pair(); frame = self.frames_b[1]; original = copy.deepcopy(frame.measurements)
        for key, value in [('image_width', 0), ('image_height', 'NaN'), ('pose_landmarks', []),
                           ('skill_phase_confidence', .2), ('measurement_space', 'legacy'), ('pose_detected', False)]:
            frame.measurements = copy.deepcopy(original); frame.measurements[key] = value
            self.assertIsNone(self.insights()['focus'], key)
        frame.measurements = copy.deepcopy(original)
        frame.measurements['pose_landmarks']['left_ankle']['x'] = 1.2
        self.assertIsNone(self.insights()['focus'])

    def test_mock_old_camera_or_changed_skill_snapshot_cannot_supply_insights(self):
        self.pair()
        for attribute, value in [('analysis_source', 'mock'), ('analysis_version', 'legacy'),
                                  ('raw_results', {'camera_view': 'front', 'selected_skill': self.video.skill_name}),
                                  ('raw_results', {'camera_view': 'side', 'selected_skill': 'Different skill'}),
                                  ('raw_results', {'camera_view': 'side', 'selected_skill': {'malformed': True}})]:
            original = getattr(self.b, attribute); setattr(self.b, attribute, value)
            self.assertFalse(self.insights()['available'], attribute)
            setattr(self.b, attribute, original)

    def test_two_unmarked_attempts_get_measurements_without_example_based_cues(self):
        self.pair(); result = self.insights(example=False)
        self.assertTrue(result['available'])
        self.assertIsNone(result['focus']); self.assertIsNone(result['strength'])

    def test_wrong_event_or_gym_and_unrelated_frame_are_rejected(self):
        self.pair(); self.assertFalse(self.insights(matching=False)['available'])
        original = self.video.gym_id; self.video.gym_id = original + 1
        self.assertFalse(self.insights()['available']); self.video.gym_id = original
        self.phases[1]['second']['frame_moment'] = self.frames_a[1]
        self.assertIsNone(self.insights()['focus'])

    def test_skill_and_title_text_are_escaped_in_the_draft(self):
        self.pair(); self.example.title = '</textarea><script>alert(1)</script>'; self.example.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('video_library:video_compare'), {'video_1': self.example.pk, 'video_2': self.video.pk})
        self.assertNotContains(response, '</textarea><script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
