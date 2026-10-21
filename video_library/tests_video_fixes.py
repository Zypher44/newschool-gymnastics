import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import IntegrityError, transaction
from django.test import TestCase, SimpleTestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership
from practice_planner.models import TrainingGroup
from .models import Video, VideoAnalysis, VideoAnalysisMoment
from .analysis_queue import enqueue_analysis, claim_analysis, finish_attempt, recover_expired_jobs
from .ai.geometry import image_plane_landmarks
from .ai.measurements import calculate_angle
from .ai.storage_files import local_storage_file
from .ai.pose_service import analyze_extracted_frames


class RemoteStorage(Storage):
    """Real bytes with the same no-local-path contract as S3 storage."""
    def __init__(self):
        self.files = {}
    def _open(self, name, mode='rb'):
        return ContentFile(self.files[name], name=name)
    def _save(self, name, content):
        self.files[name] = b''.join(content.chunks())
        return name
    def exists(self, name):
        return name in self.files
    def delete(self, name):
        self.files.pop(name, None)
    def url(self, name):
        return '/test-media/' + name
    def size(self, name):
        return len(self.files[name])


class GeometryTests(SimpleTestCase):
    def test_portrait_and_landscape_right_angles(self):
        for width, height in [(1920, 1080), (1080, 1920), (800, 800)]:
            landmarks = {name: {'x': x / width, 'y': y / height, 'visibility': .95}
                         for name, x, y in [('a', 400, 400), ('b', 300, 300), ('c', 400, 200)]}
            points = image_plane_landmarks(landmarks, width, height)
            self.assertEqual(calculate_angle(points['a'], points['b'], points['c']), 90.0)

    def test_hidden_joints_and_nonfinite_coordinates_are_omitted(self):
        points = {'hidden': {'x': .1, 'y': .2, 'visibility': .1},
                  'bad': {'x': float('nan'), 'y': .2, 'visibility': .9}}
        self.assertEqual(image_plane_landmarks(points, 1920, 1080), {})

    def test_cloud_copy_is_bounded_and_removed_on_exit(self):
        storage = RemoteStorage()
        storage.files['source.mp4'] = b'actual bytes'
        file = SimpleNamespace(storage=storage, name='source.mp4')
        with local_storage_file(file) as path:
            self.assertEqual(path.read_bytes(), b'actual bytes')
            copied = path
        self.assertFalse(copied.exists())
        with self.assertRaises(ValueError):
            with local_storage_file(file, maximum_bytes=2):
                self.fail('Oversize file should not be yielded')


class VideoFixTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gym = Gym.objects.create(name='Video test gym')
        self.owner = User.objects.create_user('video-owner', role='coach')
        self.other = User.objects.create_user('video-other', role='coach')
        self.head = User.objects.create_user('video-head', role='head_coach')
        self.athlete = User.objects.create_user('video-athlete', role='athlete')
        for user in (self.owner, self.other, self.head, self.athlete):
            GymMembership.objects.create(gym=self.gym, user=user, role=user.role)
        self.group = TrainingGroup.objects.create(gym=self.gym, name='Mixed group')
        self.group.coaches.set([self.owner, self.other])
        self.video = Video.objects.create(gym=self.gym, title='Cast handstand', skill_name='Cast Handstand',
                                          video_file='source.mp4', uploaded_by=self.owner,
                                          primary_athlete=self.athlete, training_group=self.group, status='ready', camera_view='side')

    def test_private_video_owner_only_even_for_head_coach(self):
        from .views import get_accessible_videos
        self.video.visibility = 'private'
        self.video.save()
        self.assertTrue(get_accessible_videos(self.owner).filter(pk=self.video.pk).exists())
        for coach in (self.other, self.head):
            self.assertFalse(get_accessible_videos(coach).filter(pk=self.video.pk).exists())
            self.client.force_login(coach)
            self.assertEqual(self.client.get(reverse('video_library:video_detail', args=[self.video.pk])).status_code, 404)

    def test_private_analysis_not_in_comparison_suggestions(self):
        from .views import get_comparison_candidates
        private = Video.objects.create(gym=self.gym, title='Private', skill_name=self.video.skill_name,
                                       video_file='private.mp4', uploaded_by=self.other, visibility='private',
                                       primary_athlete=self.athlete, status='ready')
        analysis = VideoAnalysis.objects.create(video=private, status='completed', raw_results={'camera_view': 'side'})
        self.assertFalse(get_comparison_candidates(self.video, self.owner).filter(pk=analysis.pk).exists())
        private.visibility = 'coaches'; private.save()
        self.assertTrue(get_comparison_candidates(self.video, self.owner).filter(pk=analysis.pk).exists())
        analysis.analysis_source = 'mock'; analysis.save()
        self.assertFalse(get_comparison_candidates(self.video, self.owner).filter(pk=analysis.pk).exists())

    def test_enqueue_deduplicates_and_keeps_completed_history(self):
        first, created = enqueue_analysis(self.video, self.owner)
        duplicate, again = enqueue_analysis(self.video, self.owner)
        self.assertTrue(created); self.assertFalse(again); self.assertEqual(first.pk, duplicate.pk)
        self.assertEqual(first.analysis_source, 'pose')
        first.status = 'completed'; first.save()
        second, created = enqueue_analysis(self.video, self.owner)
        self.assertTrue(created); self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(self.video.analyses.count(), 2)

    def test_database_prevents_duplicate_active_jobs(self):
        enqueue_analysis(self.video, self.owner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            VideoAnalysis.objects.create(video=self.video)

    def test_analysis_waits_for_conversion_and_cannot_be_claimed_twice(self):
        self.video.status = 'uploading'; self.video.save()
        analysis, _ = enqueue_analysis(self.video, self.owner)
        self.assertIsNone(claim_analysis())
        self.video.status = 'ready'; self.video.save()
        claimed = claim_analysis(timeout_seconds=10)
        self.assertEqual(claimed.pk, analysis.pk)
        self.assertEqual(claimed.processing_attempts, 1)
        self.assertIsNotNone(claimed.worker_token)
        self.assertIsNone(claim_analysis())

    def test_limited_retries_and_interrupted_worker_recovery(self):
        enqueue_analysis(self.video, self.owner)
        for attempt in (1, 2, 3):
            job = claim_analysis()
            self.assertEqual(job.processing_attempts, attempt)
            job.lease_expires_at = timezone.now() - timedelta(seconds=1); job.save()
            recover_expired_jobs(); job.refresh_from_db()
            self.assertIsNone(job.worker_token)
            self.assertEqual(job.status, 'queued' if attempt < 3 else 'failed')
            if attempt < 3:
                self.assertIsNone(claim_analysis())
                job.retry_after = timezone.now() - timedelta(seconds=1); job.save()
        self.assertIsNone(claim_analysis())

    def test_wrong_token_cannot_finish_a_job(self):
        enqueue_analysis(self.video, self.owner)
        job = claim_analysis()
        import uuid
        finish_attempt(job.pk, uuid.uuid4(), error='wrong worker')
        job.refresh_from_db(); self.assertEqual(job.status, 'preparing')

    def test_failed_conversion_does_not_leave_an_analysis_queued(self):
        job, _ = enqueue_analysis(self.video, self.owner)
        self.video.status = 'failed'; self.video.save()
        recover_expired_jobs(); job.refresh_from_db()
        self.assertEqual(job.status, 'failed')

    def test_newer_request_is_not_overwritten_by_an_old_failed_worker(self):
        enqueue_analysis(self.video, self.owner)
        old = claim_analysis(); old.status = 'failed'; old.save()
        new, _ = enqueue_analysis(self.video, self.owner)
        finish_attempt(old.pk, old.worker_token, error='old failed')
        old.refresh_from_db(); new.refresh_from_db(); self.video.refresh_from_db()
        self.assertEqual(old.status, 'failed'); self.assertEqual(new.status, 'queued')
        self.assertEqual(self.video.ai_status, 'queued')

    def test_http_request_queues_and_does_not_run_native_analysis(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('video_library:request_analysis', args=[self.video.pk]))
        self.assertEqual(response.status_code, 302)
        job = self.video.analyses.get()
        self.assertEqual(job.status, 'queued'); self.assertEqual(job.processing_attempts, 0)
        response = self.client.post(reverse('video_library:process_mock_analysis', args=[job.pk]))
        self.assertEqual(response.status_code, 202)
        job.refresh_from_db(); self.assertEqual(job.status, 'queued')

    def test_upload_checkbox_creates_job_and_waits_for_conversion(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        storage = RemoteStorage()
        field = Video._meta.get_field('video_file')
        self.client.force_login(self.owner)
        with patch.object(field, 'storage', storage):
            response = self.client.post(reverse('video_library:upload'), {
                'videos': SimpleUploadedFile('attempt.mp4', b'test upload', content_type='video/mp4'),
                'event': 'bars', 'video_type': 'practice', 'visibility': 'coaches',
                'request_ai_analysis': 'on', 'skill_name': 'Cast Handstand',
                'camera_view': 'front',
            })
        self.assertEqual(response.status_code, 302)
        uploaded = Video.objects.exclude(pk=self.video.pk).get()
        self.assertEqual(uploaded.status, 'uploading')
        self.assertEqual(uploaded.analyses.get().status, 'queued')
        self.assertEqual(uploaded.camera_view, 'front')
        self.assertEqual(uploaded.analyses.get().raw_results['camera_view'], 'front')
        self.assertIsNone(claim_analysis())

    def test_status_and_both_pages_render_progress_without_demo_confidence(self):
        job, _ = enqueue_analysis(self.video, self.owner)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('video_library:analysis_status', args=[job.pk]))
        self.assertEqual(response.status_code, 200); self.assertFalse(response.json()['is_finished'])
        for name, pk in [('video_detail', self.video.pk), ('analysis_detail', job.pk)]:
            response = self.client.get(reverse('video_library:' + name, args=[pk]))
            self.assertContains(response, 'data-video-analysis-panel')
            self.assertNotContains(response, '91%')
            self.assertNotContains(response, 'data-process-url')
        self.client.force_login(self.athlete)
        self.assertEqual(self.client.get(reverse('video_library:analysis_status', args=[job.pk])).status_code, 403)

    def test_missing_pose_clears_stale_results_and_uses_remote_images(self):
        storage = RemoteStorage()
        image = io.BytesIO(); Image.new('RGB', (1920, 1080)).save(image, format='JPEG')
        storage.files['frame.jpg'] = image.getvalue()
        field = VideoAnalysisMoment._meta.get_field('frame_image')
        job, _ = enqueue_analysis(self.video, self.owner)
        moment = VideoAnalysisMoment.objects.create(analysis=job, timestamp_seconds=0, frame_image='frame.jpg',
            measurements={'pose_landmarks': {'old': {}}, 'gymnastics_measurements': {'old': 123}})
        class EmptyEngine:
            closed = False
            def analyze_image(self, path):
                return SimpleNamespace(detected=False, landmarks=[], landmark_count=0)
            def close(self):
                self.closed = True
        engine = EmptyEngine()
        with patch.object(field, 'storage', storage):
            result = analyze_extracted_frames(job, engine=engine)
        moment.refresh_from_db()
        self.assertTrue(engine.closed); self.assertEqual(result['frames_with_pose'], 0)
        self.assertEqual(moment.measurements['gymnastics_measurements'], {})
        self.assertEqual(moment.measurements['pose_landmarks'], {})

    def test_evidence_engine_has_no_synthetic_skill_or_confidence(self):
        from .ai.evidence_engine import EvidenceAnalysisEngine
        job, _ = enqueue_analysis(self.video, self.owner)
        result = EvidenceAnalysisEngine().analyze(job)
        self.assertIsNone(result.skill_confidence); self.assertEqual(result.detected_skill, '')
        self.assertFalse(result.raw_results['mock_analysis'])
        self.assertNotIn('shoulder_angle_degrees', result.measurements)
        self.assertEqual(result.strengths, [])

    def test_camera_view_snapshot_gates_technique_cues(self):
        from .ai.skill_analysis_service import generate_skill_observations
        from .ai.evidence_engine import EvidenceAnalysisEngine
        self.video.camera_view = 'unknown'; self.video.save()
        job, _ = enqueue_analysis(self.video, self.owner)
        self.video.camera_view = 'side'; self.video.save()
        job.video = self.video
        VideoAnalysisMoment.objects.create(analysis=job, timestamp_seconds=0, frame_image='frame.jpg',
            measurements={'pose_detected': True, 'skill_phase': 'entry', 'skill_phase_confidence': .95,
                          'pose_angles': {'left_knee_angle': 90},
                          'gymnastics_measurements': {'average_landmark_visibility': .95, 'knee_extension': {'average_angle': 90}}})
        self.assertEqual(generate_skill_observations(job)['observations_created'], 0)
        result = EvidenceAnalysisEngine().analyze(job)
        self.assertEqual(result.raw_results['camera_view'], 'unknown')
        self.assertFalse(result.raw_results['technique_available'])
        self.assertEqual(result.improvements, [])
        job.raw_results = {'camera_view': 'side'}; job.save()
        self.assertGreater(generate_skill_observations(job)['observations_created'], 0)
        self.assertTrue(EvidenceAnalysisEngine().analyze(job).raw_results['technique_available'])

    def test_native_pipeline_and_conversion_use_cloud_storage_without_paths(self):
        import cv2
        import numpy as np
        from contextlib import ExitStack
        from .ai.conversion_service import convert_video_to_mp4
        from .ai.video_service import process_video_file
        from .ai.processor import VideoAnalysisProcessor
        storage = RemoteStorage()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'blank.mp4'
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (320, 240))
            self.assertTrue(writer.isOpened())
            for _ in range(20):
                writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
            writer.release()
            storage.files['source.mp4'] = path.read_bytes()
        with ExitStack() as stack:
            for model, name in [(Video, 'video_file'), (Video, 'thumbnail'),
                                (VideoAnalysisMoment, 'frame_image'), (VideoAnalysisMoment, 'annotated_frame_image')]:
                stack.enter_context(patch.object(model._meta.get_field(name), 'storage', storage))
            video = Video.objects.get(pk=self.video.pk)
            original = video.video_file.name
            convert_video_to_mp4(video)
            self.assertNotIn(original, storage.files)
            self.assertIn(video.video_file.name, storage.files)
            metadata = process_video_file(video)
            self.assertEqual((metadata.width, metadata.height), (320, 240))
            enqueue_analysis(video, self.owner)
            job = claim_analysis()
            VideoAnalysisProcessor().process(job)
            job.refresh_from_db(); video.refresh_from_db()
            self.assertEqual(job.status, 'completed'); self.assertEqual(job.analysis_source, 'pose')
            self.assertIsNone(job.skill_confidence)
            self.assertFalse(job.raw_results['mock_analysis'])
            self.assertEqual(job.measurements['frames_with_pose'], 0)
            self.assertGreater(job.measurements['sampled_frames'], 0)
            self.assertEqual(video.ai_status, 'completed')
            self.assertFalse(video.ai_results['mock_analysis'])
            finish_attempt(job.pk, job.worker_token)

    def test_worker_timeout_requeues_without_blocking_a_web_request(self):
        import subprocess
        from django.core.management import call_command
        enqueue_analysis(self.video, self.owner)
        with patch('video_library.management.commands.process_video_analysis_queue.subprocess.run',
                   side_effect=subprocess.TimeoutExpired('processor', 1)) as run, \
             patch.object(self.video.video_file.storage, 'exists', return_value=True):
            call_command('process_video_analysis_queue', once=True, timeout_seconds=1, stdout=io.StringIO())
        self.assertEqual(run.call_args.kwargs['timeout'], 11)
        job = self.video.analyses.get()
        self.assertEqual(job.status, 'queued'); self.assertEqual(job.processing_attempts, 1)
        self.assertIsNone(job.worker_token)


class LegacyQueueMigrationTests(TransactionTestCase):
    def test_legacy_duplicates_are_preserved_without_blocking_migration(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        executor.migrate([('video_library', '0011_video_mock_meet_type')])
        try:
            state = executor.loader.project_state([('video_library', '0011_video_mock_meet_type')]).apps
            OldVideo = state.get_model('video_library', 'Video')
            OldAnalysis = state.get_model('video_library', 'VideoAnalysis')
            video = OldVideo.objects.create(title='Historical video', video_file='old.mp4')
            checkbox_video = OldVideo.objects.create(title='Queued by old upload checkbox', video_file='checkbox.mp4', ai_status='queued')
            older = OldAnalysis.objects.create(video=video, status='processing', analysis_source='mock')
            newer = OldAnalysis.objects.create(video=video, status='queued', analysis_source='mock')
            history = OldAnalysis.objects.create(video=video, status='completed', analysis_source='mock',
                                                 summary='Historical demonstration', coach_review_notes='Keep this review')
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate([('video_library', '0012_analysis_queue')])
        self.assertEqual(VideoAnalysis.objects.get(pk=older.pk).status, 'cancelled')
        self.assertEqual(VideoAnalysis.objects.get(pk=newer.pk).status, 'queued')
        saved = VideoAnalysis.objects.get(pk=history.pk)
        self.assertEqual(saved.summary, 'Historical demonstration')
        self.assertEqual(saved.coach_review_notes, 'Keep this review')
        self.assertEqual(VideoAnalysis.objects.filter(video_id=video.pk).count(), 3)
        repaired = VideoAnalysis.objects.get(video_id=checkbox_video.pk)
        self.assertEqual(repaired.status, 'queued')
        self.assertEqual(repaired.analysis_source, 'pose')
