import importlib
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from gyms.models import Gym, GymMembership
from .tests_reference_examples import ReferenceExampleTests
from .models import Video
from .reference_examples import get_coaching_examples
from .skill_library import is_approved
from .skill_library_forms import SkillExampleForm


class SkillLibraryTests(TestCase):
    setUp = ReferenceExampleTests.setUp
    create = ReferenceExampleTests.create

    def login(self, user=None):
        self.client.force_login(user or self.owner)

    def url(self, name, video=None):
        return reverse('video_library:' + name, args=[video.pk] if video else [])

    def test_library_is_accessible_from_both_video_entry_points(self):
        self.login()
        for name in ('dashboard', 'video_list'):
            response = self.client.get(self.url(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.url('skill_library'))
            self.assertContains(response, 'Approved Skill Library')
        response = self.client.get(self.url('skill_library'))
        self.assertContains(response, self.example.title)
        self.assertNotContains(response, 'My attempt</h2>')
        self.assertEqual(response.context['counts']['approved'], 1)

    def test_upload_is_coach_shared_pending_and_uses_existing_queue(self):
        self.login()
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post(self.url('skill_example_upload'), {
                'title': 'Coach demo', 'event': 'bars', 'skill_name': '  Cast   Handstand  ',
                'camera_view': 'side', 'analyze': 'on', 'notes': 'Long body shape.',
                'video': SimpleUploadedFile('demo.mov', b'fake video for upload test', content_type='video/quicktime'),
                'gym_id': '999', 'visibility': 'parents', 'primary_athlete': self.athlete.pk,
            })
            self.assertEqual(response.status_code, 302)
            video = Video.objects.get(title='Coach demo')
            self.assertEqual(video.gym_id, self.gym.pk)
            self.assertEqual(video.visibility, 'coaches')
            self.assertIsNone(video.primary_athlete_id); self.assertIsNone(video.training_group_id)
            self.assertEqual(video.skill_name, 'Cast Handstand')
            self.assertEqual(video.status, 'uploading')
            self.assertFalse(is_approved(video)); self.assertTrue(video.is_skill_library_video)
            self.assertEqual(video.analyses.get().status, 'queued')
            self.assertEqual(video.analyses.get().requested_by_id, self.owner.pk)
            self.assertTrue(Path(directory, video.video_file.name).is_file())
            self.assertNotIn(video, get_coaching_examples(self.video, self.owner))
            response = self.client.get(self.url('skill_library'), {'state': 'pending'})
            self.assertContains(response, 'Coach demo')
            self.assertEqual(response.context['counts']['pending'], 1)

    def test_upload_can_skip_analysis_and_rejects_bad_files(self):
        self.login(); data = {'title': 'No analysis', 'event': 'bars', 'skill_name': 'Cast Handstand', 'camera_view': 'side'}
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post(self.url('skill_example_upload'), {**data,
                    'video': SimpleUploadedFile('demo.mp4', b'video', content_type='video/mp4')})
            self.assertEqual(response.status_code, 302)
            self.assertFalse(Video.objects.get(title='No analysis').analyses.exists())
        form = SkillExampleForm(data, {'video': SimpleUploadedFile('evil.exe', b'bad', content_type='video/mp4')})
        self.assertFalse(form.is_valid()); self.assertIn('video', form.errors)
        huge = SimpleUploadedFile('demo.mp4', b'video', content_type='video/mp4'); huge.size = 501 * 1024 * 1024
        form = SkillExampleForm(data, {'video': huge}); self.assertFalse(form.is_valid())
        form = SkillExampleForm(data, {'video': SimpleUploadedFile('demo.mp4', b'bad', content_type='text/plain')})
        self.assertFalse(form.is_valid())

    def test_approval_requires_ready_source_and_explicit_review_confirmation(self):
        pending = self.create(is_coaching_example=False, is_skill_library_video=True, status='uploading')
        self.login()
        response = self.client.post(self.url('approve_skill_example', pending), {'confirmed': 'on'})
        self.assertEqual(response.status_code, 302); pending.refresh_from_db(); self.assertFalse(is_approved(pending))
        pending.status = 'ready'; pending.save()
        self.client.post(self.url('approve_skill_example', pending), {})
        pending.refresh_from_db(); self.assertFalse(is_approved(pending))
        self.client.post(self.url('approve_skill_example', pending), {'confirmed': 'on'})
        pending.refresh_from_db(); self.assertTrue(is_approved(pending))
        self.assertEqual(pending.skill_library_approved_by_id, self.owner.pk)
        date = pending.skill_library_approved_at
        self.client.post(self.url('approve_skill_example', pending), {'confirmed': 'on'})
        pending.refresh_from_db(); self.assertEqual(pending.skill_library_approved_at, date)
        self.assertIn(pending, get_coaching_examples(self.video, self.owner))
        response = self.client.get(self.url('skill_example_detail', pending))
        self.assertContains(response, 'Coach Approved')
        self.assertContains(response, f'name="video_1" value="{pending.pk}"')
        self.assertContains(response, f'<option value="{self.video.pk}">')

    def test_existing_video_without_skill_metadata_can_enter_review_then_be_edited(self):
        self.video.skill_name = ''; self.video.save(); self.login()
        response = self.client.post(self.url('add_skill_example', self.video))
        self.assertEqual(response.status_code, 302); self.video.refresh_from_db()
        self.assertTrue(self.video.is_skill_library_video); self.assertFalse(is_approved(self.video))
        response = self.client.post(self.url('skill_example_edit', self.video), {
            'title': self.video.title, 'event': 'bars', 'skill_name': 'Cast Handstand',
            'camera_view': 'side', 'notes': 'Example teaching note.'})
        self.assertEqual(response.status_code, 302)
        self.client.post(self.url('approve_skill_example', self.video), {'confirmed': 'on'})
        self.video.refresh_from_db(); self.assertTrue(is_approved(self.video))

    def test_existing_video_can_be_approved_without_copying_file_or_sharing_private_video(self):
        self.video.visibility = 'private'; self.video.save(); original = self.video.video_file.name
        self.login(); self.client.post(self.url('toggle_coaching_example', self.video))
        self.video.refresh_from_db(); self.assertTrue(is_approved(self.video))
        self.assertEqual(self.video.video_file.name, original); self.assertEqual(self.video.visibility, 'private')
        self.login(self.other)
        self.assertEqual(self.client.get(self.url('skill_example_detail', self.video)).status_code, 404)

    def test_approval_record_does_not_change_when_an_athlete_reference_is_marked(self):
        self.login(self.other); old_coach = self.example.skill_library_approved_by_id; old_time = self.example.skill_library_approved_at
        self.client.post(self.url('toggle_reference_attempt', self.example))
        self.client.post(self.url('toggle_personal_best', self.example))
        self.example.refresh_from_db()
        self.assertEqual(self.example.skill_library_approved_by_id, old_coach)
        self.assertEqual(self.example.skill_library_approved_at, old_time)

    def test_editing_technique_metadata_revokes_approval_but_notes_do_not(self):
        self.login(); data = {'title': self.example.title, 'event': 'bars', 'skill_name': 'Cast Handstand',
                              'camera_view': self.example.camera_view, 'notes': 'Updated coach teaching note.'}
        self.client.post(self.url('skill_example_edit', self.example), data)
        self.example.refresh_from_db(); self.assertTrue(is_approved(self.example))
        data.update(skill_name='Back Tuck', event='floor')
        self.client.post(self.url('skill_example_edit', self.example), data)
        self.example.refresh_from_db(); self.assertFalse(is_approved(self.example))
        self.assertTrue(self.example.is_skill_library_video)
        self.assertFalse(get_coaching_examples(self.video, self.owner).exists())

    def test_changing_camera_on_regular_video_page_revokes_library_approval(self):
        self.login(); self.client.post(self.url('update_camera_view', self.example), {'camera_view': 'front'})
        self.example.refresh_from_db(); self.assertFalse(is_approved(self.example))

    def test_remove_preserves_source_and_athlete_reference(self):
        self.example.is_reference_attempt = True; self.example.save(); file = self.example.video_file.name
        self.login(); response = self.client.post(self.url('remove_skill_example', self.example))
        self.assertEqual(response.status_code, 302); self.example.refresh_from_db()
        self.assertEqual(self.example.video_file.name, file); self.assertTrue(self.example.is_reference_attempt)
        self.assertFalse(self.example.is_skill_library_video); self.assertFalse(is_approved(self.example))
        self.assertFalse(get_coaching_examples(self.video, self.owner).exists())

    def test_other_coach_can_approve_accessible_example_but_cannot_edit_or_remove_others_approval(self):
        self.login(self.other)
        for name in ('skill_example_edit', 'remove_skill_example', 'update_camera_view', 'update_video_sharing'):
            response = self.client.post(self.url(name, self.example), {})
            self.assertEqual(response.status_code, 403)
        pending = self.create(is_coaching_example=False, is_skill_library_video=True)
        self.client.post(self.url('approve_skill_example', pending), {'confirmed': 'on'})
        pending.refresh_from_db(); self.assertEqual(pending.skill_library_approved_by_id, self.other.pk)

    def test_foreign_gym_private_video_and_inactive_membership_are_blocked(self):
        foreign = self.create(gym=Gym.objects.create(name='Foreign library'))
        self.login()
        for video in (foreign, self.create(visibility='private', uploaded_by=self.other)):
            for name in ('skill_example_detail', 'skill_example_edit', 'approve_skill_example', 'remove_skill_example'):
                response = self.client.post(self.url(name, video), {'confirmed': 'on'})
                self.assertEqual(response.status_code, 404, name)
        GymMembership.objects.filter(user=self.owner).update(is_active=False)
        self.assertEqual(self.client.get(self.url('skill_library')).status_code, 403)

    def test_access_is_rechecked_after_a_video_lock_wait(self):
        pending = self.create(is_coaching_example=False, is_skill_library_video=True)
        self.login()
        with patch('video_library.skill_library_views.accessible', side_effect=[
                Video.objects.filter(pk=pending.pk), Video.objects.none()]):
            response = self.client.post(self.url('approve_skill_example', pending), {'confirmed': 'on'})
        self.assertEqual(response.status_code, 404)
        pending.refresh_from_db(); self.assertFalse(is_approved(pending))

    def test_athletes_parents_and_multiple_gym_coaches_cannot_access_library(self):
        parent = get_user_model().objects.create_user('library-parent', role='parent')
        for user in (self.athlete, parent):
            self.login(user)
            for name in ('skill_library', 'skill_example_upload'):
                self.assertEqual(self.client.get(self.url(name)).status_code, 403)
            self.assertEqual(self.client.post(self.url('approve_skill_example', self.example), {'confirmed': 'on'}).status_code, 403)
        GymMembership.objects.create(gym=Gym.objects.create(name='Ambiguous gym'), user=self.owner, role='coach')
        self.login(); self.assertEqual(self.client.get(self.url('skill_library')).status_code, 403)

    def test_head_coach_can_manage_gym_examples_and_mutations_require_post_and_csrf(self):
        head = get_user_model().objects.create_user('library-head', role='head_coach')
        GymMembership.objects.create(gym=self.gym, user=head, role='head_coach'); self.login(head)
        self.assertEqual(self.client.get(self.url('skill_example_edit', self.example)).status_code, 200)
        self.assertEqual(self.client.get(self.url('remove_skill_example', self.example)).status_code, 405)
        self.assertEqual(self.client.get(self.url('approve_skill_example', self.example)).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True); csrf_client.force_login(head)
        self.assertEqual(csrf_client.post(self.url('remove_skill_example', self.example)).status_code, 403)

    def test_matching_examples_support_skill_aliases_and_attempt_picker_cannot_leak_foreign_video(self):
        self.video.skill_name = 'Cast to Handstand'; self.video.save()
        self.assertEqual(list(get_coaching_examples(self.video, self.owner)), [self.example])
        self.login(); response = self.client.get(self.url('skill_example_detail', self.example))
        self.assertContains(response, f'<option value="{self.video.pk}">')
        foreign = self.create(gym=Gym.objects.create(name='Foreign attempts'))
        self.assertEqual(self.client.get(self.url('skill_library'), {'attempt': foreign.pk}).status_code, 404)
        response = self.client.get(self.url('skill_library'), {'attempt': self.video.pk})
        self.assertContains(response, f'video_1={self.example.pk}&amp;video_2={self.video.pk}')

    def test_search_pending_filters_and_html_escaping(self):
        pending = self.create(title='Pending', is_coaching_example=False, is_skill_library_video=True)
        self.example.notes = '<script>attack</script>'; self.example.save()
        self.login(); response = self.client.get(self.url('skill_example_detail', self.example))
        self.assertContains(response, '&lt;script&gt;attack&lt;/script&gt;')
        self.assertNotContains(response, '<script>attack</script>')
        response = self.client.get(self.url('skill_library'), {'state': 'pending'})
        self.assertEqual(list(response.context['page_obj']), [pending])
        response = self.client.get(self.url('skill_library'), {'q': 'no matching title', 'event': 'floor'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_legacy_marked_examples_migrate_only_with_real_matching_coach_history(self):
        self.example.is_skill_library_video = False; self.example.skill_library_approved_by = None
        self.example.skill_library_approved_at = None; self.example.save()
        untrusted = self.create(reference_marked_by=self.athlete, skill_library_approved_by=None,
                                skill_library_approved_at=None, is_skill_library_video=False)
        missing_date = self.create(reference_marked_at=None, skill_library_approved_by=None,
                                   skill_library_approved_at=None, is_skill_library_video=False)
        ambiguous = self.create(is_reference_attempt=True, skill_library_approved_by=None,
                                skill_library_approved_at=None, is_skill_library_video=False)
        migration = importlib.import_module('video_library.migrations.0013_approved_skill_library')
        migration.preserve_marked_examples(apps, SimpleNamespace(connection=connection))
        self.example.refresh_from_db(); untrusted.refresh_from_db(); missing_date.refresh_from_db()
        ambiguous.refresh_from_db()
        self.assertTrue(is_approved(self.example))
        self.assertEqual(self.example.skill_library_approved_at, self.example.reference_marked_at)
        self.assertFalse(is_approved(untrusted)); self.assertFalse(is_approved(missing_date))
        self.assertFalse(is_approved(ambiguous))
        self.assertTrue(untrusted.is_skill_library_video)
