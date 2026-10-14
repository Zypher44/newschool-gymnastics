import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from gyms.models import GymMembership
from . import tests_video_progress as fixtures
from .models import Video, VideoMomentNote


class VideoMomentFeedbackTests(TestCase):
    setUp = fixtures.VideoProgressTests.setUp
    create = fixtures.VideoProgressTests.create
    login = fixtures.VideoProgressTests.login

    def url(self, video=None, note=None):
        args = [(video or self.first).pk]
        if note is not None:
            args.append(note.pk)
        return reverse('video_library:change_video_moment' if note else 'video_library:video_moments', args=args)

    def post(self, data, video=None, note=None, client=None):
        return (client or self.client).post(self.url(video, note), data=json.dumps(data), content_type='application/json')

    def saved(self, **extra):
        fields = dict(video=self.first, author=self.coach, timestamp_seconds=Decimal('8.25'),
                      comment='Extend through the shoulders.', visibility='private', drawing=[])
        fields.update(extra)
        return VideoMomentNote.objects.create(**fields)

    def shape(self, tool='arrow'):
        return dict(tool=tool, color='#ef4444', points=[[0.1, 0.25], [0.8, 0.5]])

    def test_create_defaults_private_and_retains_timestamp_and_normalized_drawing(self):
        self.login()
        response = self.post(dict(timestamp_seconds=8.1235, comment='  Tall shape.  ', drawing=[self.shape()]))
        self.assertEqual(response.status_code, 201)
        note = VideoMomentNote.objects.get()
        self.assertEqual(note.timestamp_seconds, Decimal('8.124'))
        self.assertEqual(note.comment, 'Tall shape.')
        self.assertEqual(note.drawing, [self.shape()])
        self.assertEqual(note.visibility, 'private')
        self.assertTrue(response.json()['note']['can_edit'])
        self.assertIn('no-store', response['Cache-Control'])
        for user in (self.head, self.parent, self.athlete):
            self.login(user)
            self.assertEqual(self.client.get(self.url()).json()['notes'], [])

    def test_private_coach_athlete_parent_audiences_do_not_leak(self):
        for visibility in ('private', 'coaches', 'athlete', 'parents'):
            self.saved(visibility=visibility, comment=visibility)
        for user, allowed in ((self.coach, {'private', 'coaches', 'athlete', 'parents'}),
                              (self.head, {'coaches', 'athlete', 'parents'}),
                              (self.athlete, {'athlete', 'parents'}), (self.parent, {'parents'})):
            self.login(user)
            body = self.client.get(self.url()).json()
            self.assertEqual({note['comment'] for note in body['notes']}, allowed)
            if user.role in ('parent', 'athlete'):
                self.assertFalse(any(note['can_edit'] for note in body['notes']))

    def test_comment_only_and_drawing_only_are_supported(self):
        self.login()
        self.assertEqual(self.post(dict(timestamp_seconds=0, comment='Start position.')).status_code, 201)
        self.assertEqual(self.post(dict(timestamp_seconds=2, drawing=[self.shape('circle')])).status_code, 201)
        self.assertEqual(self.post(dict(timestamp_seconds=2, comment=' ')).status_code, 400)

    def test_bad_timestamps_and_out_of_range_moments_are_rejected(self):
        self.first.duration_seconds = 10
        self.first.save()
        self.login()
        for timestamp in (-1, 'nan', 'inf', True, None, [], 10.5, 21601):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(self.post(dict(timestamp_seconds=timestamp, comment='Cue')).status_code, 400)
        self.assertEqual(VideoMomentNote.objects.count(), 0)

    def test_shape_validation_rejects_markup_bad_coordinates_and_oversized_payloads(self):
        self.login()
        invalid = [dict(tool='<script>', color='#ef4444', points=[[0, 0], [1, 1]]),
                   dict(tool='arrow', color='url(javascript:alert(1))', points=[[0, 0], [1, 1]]),
                   dict(tool='line', color='#ef4444', points=[[True, 0], [1, 1]]),
                   dict(tool='line', color='#ef4444', points=[[-0.1, 0], [1, 1]]),
                   dict(tool='line', color='#ef4444', points=[[0, 0], [1.1, 1]]),
                   dict(tool='line', color='#ef4444', points=[[0, 0], [float('nan'), 1]]),
                   dict(tool='line', color='#ef4444', points=[[0, 0], [10**400, 1]]),
                   dict(tool='line', color='#ef4444', points=[[0, 0], [0.5, 0.5], [1, 1]]),
                   dict(tool='pen', color='#ef4444', points=[[0, 0]] * 401),
                   dict(self.shape(), svg='<script>')]
        for shape in invalid:
            self.assertEqual(self.post(dict(timestamp_seconds=1, drawing=[shape])).status_code, 400)
        for visibility in ({}, [], False, 'public'):
            self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue', visibility=visibility)).status_code, 400)
        self.assertEqual(self.post(dict(timestamp_seconds=1, drawing=[self.shape()] * 51)).status_code, 400)
        self.assertEqual(self.post(dict(timestamp_seconds=1, comment='x' * 2501)).status_code, 400)
        response = self.client.post(self.url(), data='x' * 131073, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VideoMomentNote.objects.count(), 0)

    def test_share_feedback_does_not_publish_a_hidden_video(self):
        self.first.visibility = 'coaches'
        self.first.save()
        self.login()
        for visibility in ('athlete', 'parents'):
            self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue', visibility=visibility)).status_code, 400)
        self.first.refresh_from_db()
        self.assertEqual(self.first.visibility, 'coaches')
        self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue', visibility='coaches')).status_code, 201)
        self.first.visibility = 'athlete'
        self.first.save()
        self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue', visibility='athlete')).status_code, 201)
        self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue', visibility='parents')).status_code, 400)

    def test_owner_can_edit_delete_and_stale_versions_do_not_overwrite(self):
        note = self.saved()
        original_revision = note.updated_at.isoformat()
        self.login()
        data = dict(action='update', updated_at=original_revision, timestamp_seconds=9,
                    comment='Updated cue', visibility='parents', drawing=[self.shape('line')])
        response = self.post(data, note=note)
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.author, self.coach)
        self.assertEqual(note.comment, 'Updated cue')
        self.assertEqual(self.post(data, note=note).status_code, 409)
        self.assertEqual(self.post(dict(action='delete', updated_at=original_revision), note=note).status_code, 409)
        self.assertEqual(self.post(dict(action='delete', updated_at=note.updated_at.isoformat()), note=note).status_code, 200)
        self.assertFalse(VideoMomentNote.objects.exists())

    def test_other_coach_cannot_edit_and_head_coach_cannot_read_private_notes(self):
        other = get_user_model().objects.create_user('feedback-other', role='coach')
        GymMembership.objects.create(gym=self.gym, user=other, role='coach')
        private = self.saved()
        shared = self.saved(visibility='coaches')
        self.login(other)
        self.assertEqual(self.post(dict(action='delete', updated_at=shared.updated_at.isoformat()), note=shared).status_code, 403)
        self.assertEqual(self.post(dict(action='delete', updated_at=private.updated_at.isoformat()), note=private).status_code, 404)
        self.login(self.head)
        self.assertEqual(self.post(dict(action='delete', updated_at=private.updated_at.isoformat()), note=private).status_code, 404)
        self.assertEqual(self.post(dict(action='update', updated_at=shared.updated_at.isoformat(),
                                        timestamp_seconds=8, comment='Reviewed cue', visibility='coaches'), note=shared).status_code, 200)
        shared.refresh_from_db()
        self.assertEqual(shared.author, self.coach)

    def test_family_cannot_mutate_feedback_even_if_they_can_read_it(self):
        note = self.saved(visibility='parents')
        for user in (self.parent, self.athlete):
            self.login(user)
            self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Injected')).status_code, 403)
            self.assertEqual(self.post(dict(action='delete', updated_at=note.updated_at.isoformat()), note=note).status_code, 403)
        self.assertEqual(VideoMomentNote.objects.count(), 1)

    def test_coach_gym_private_video_and_parent_revocation_are_enforced(self):
        hidden = self.create(gym=self.foreign_gym, title='Foreign')
        private = self.create(uploaded_by=self.head, visibility='private')
        self.login()
        for video in (hidden, private):
            self.assertEqual(self.client.get(self.url(video)).status_code, 404)
            self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Injected'), video=video).status_code, 404)
        self.login(self.parent)
        self.assertEqual(self.client.get(self.url(hidden)).status_code, 404)
        self.link.approved = False
        self.link.save()
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_parent_cannot_read_childs_other_gym_without_active_child_membership(self):
        GymMembership.objects.create(gym=self.foreign_gym, user=self.parent, role='parent')
        GymMembership.objects.create(gym=self.foreign_gym, user=self.athlete, role='athlete', is_active=False)
        video = self.create(gym=self.foreign_gym)
        self.login(self.parent)
        self.assertEqual(self.client.get(self.url(video)).status_code, 404)

    def test_pagination_is_scoped_and_timestamp_ordered(self):
        for index in range(55):
            self.saved(visibility='parents', timestamp_seconds=index / 10)
        self.saved(visibility='private')
        self.login(self.parent)
        first_page = self.client.get(self.url()).json()
        self.assertEqual(len(first_page['notes']), 50)
        self.assertEqual(first_page['next_page'], 2)
        second_page = self.client.get(self.url(), {'page': 2}).json()
        self.assertEqual(len(second_page['notes']), 5)
        self.assertIsNone(second_page['next_page'])
        times = [note['timestamp_seconds'] for note in first_page['notes'] + second_page['notes']]
        self.assertEqual(times, sorted(times))

    def test_player_pages_and_family_links_render_correct_controls(self):
        self.login()
        response = self.client.get(reverse('video_library:video_detail', args=[self.first.pk]))
        self.assertContains(response, 'id="vm-detail-player"')
        self.assertContains(response, 'data-draw-new')
        self.assertContains(response, 'video-moments.js')
        self.login(self.parent)
        response = self.client.get(reverse('video_library:moment_feedback', args=[self.first.pk]))
        self.assertContains(response, 'data-video-moments')
        self.assertNotContains(response, 'data-editor')
        self.assertNotContains(response, 'data-draw-new')
        self.assertContains(self.client.get(reverse('video_library:family_library')), 'View moment feedback')
        self.assertContains(self.client.get(reverse('parent_video_detail', args=[self.first.pk])), 'vm-parent-player')

    def test_csrf_is_required_and_get_cannot_delete(self):
        note = self.saved()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.coach)
        response = self.post(dict(timestamp_seconds=1, comment='Cue'), client=client)
        self.assertEqual(response.status_code, 403)
        client.get(reverse('video_library:video_detail', args=[self.first.pk]))
        token = client.cookies['csrftoken'].value
        response = client.post(self.url(), data=json.dumps(dict(timestamp_seconds=1, comment='Cue')),
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(client.get(self.url(note=note)).status_code, 405)
        self.assertEqual(VideoMomentNote.objects.count(), 2)

    def test_not_ready_video_rejects_mutation_without_creating_a_note(self):
        self.first.status = 'uploading'
        self.first.save()
        self.login()
        self.assertEqual(self.post(dict(timestamp_seconds=1, comment='Cue')).status_code, 400)
        self.assertFalse(VideoMomentNote.objects.exists())

    def test_skill_library_example_has_the_same_drawing_and_comment_controls(self):
        self.first.is_skill_library_video = True
        self.first.save()
        self.login()
        response = self.client.get(reverse('video_library:skill_example_detail', args=[self.first.pk]))
        self.assertContains(response, 'vm-skill-example-player')
        self.assertContains(response, 'data-draw-new')
