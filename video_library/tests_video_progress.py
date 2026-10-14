from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from coaches.models import CoachAthleteAssignment
from gyms.models import Gym, GymMembership
from parents_portal.models import ParentAthleteLink
from practice_planner.models import TrainingGroup

from .models import Video


class VideoProgressTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gym = Gym.objects.create(name='Progress gym')
        self.foreign_gym = Gym.objects.create(name='Other gym')
        self.coach = User.objects.create_user('progress-coach', role='coach')
        self.head = User.objects.create_user('progress-head', role='head_coach')
        self.athlete = User.objects.create_user('progress-child', role='athlete')
        self.other_child = User.objects.create_user('other-child', role='athlete')
        self.parent = User.objects.create_user('progress-parent', role='parent')
        for user in (self.coach, self.head, self.athlete, self.other_child, self.parent):
            GymMembership.objects.create(gym=self.gym, user=user, role=user.role)
        self.link = ParentAthleteLink.objects.create(parent=self.parent, athlete=self.athlete, approved=True)
        self.now = timezone.now()
        self.first = self.create(title='First cast', recorded_at=self.now - timedelta(days=60))
        self.latest = self.create(title='Latest cast', recorded_at=self.now - timedelta(days=1))

    def create(self, **extra):
        data = dict(gym=self.gym, primary_athlete=self.athlete, uploaded_by=self.coach,
                    title='Attempt', skill_name='Cast Handstand', event='bars', camera_view='side',
                    status='ready', video_file='videos/attempt.mp4', visibility='parents')
        data.update(extra)
        return Video.objects.create(**data)

    def url(self, athlete=None):
        return reverse('video_library:athlete_timeline', args=[(athlete or self.athlete).pk])

    def login(self, user=None):
        self.client.force_login(user or self.coach)

    def test_chronology_uses_recording_date_and_upload_fallback_with_stable_ties(self):
        middle = self.create(title='Uploaded middle', recorded_at=None)
        Video.objects.filter(pk=middle.pk).update(uploaded_at=self.now - timedelta(days=30))
        tied = self.create(title='Tied latest', recorded_at=self.latest.recorded_at)
        self.login()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([v.pk for v in response.context['page_obj']],
                         [self.first.pk, middle.pk, self.latest.pk, tied.pk])
        pair = response.context['comparison']
        self.assertEqual(pair['first'].pk, self.first.pk)
        self.assertEqual(pair['current'].pk, tied.pk)
        self.assertContains(response, 'Uploaded')
        self.assertContains(response, 'compare-video-a')
        self.assertContains(response, 'free-comparison.js')

    def test_same_skill_is_grouped_by_event_and_drills_routines_remain_separate(self):
        normalized = self.create(skill_name='  CAST   handstand  ')
        self.create(event='beam')
        self.create(video_type='drill')
        self.create(video_type='routine')
        self.login()
        response = self.client.get(self.url(), {'event': 'bars', 'skill': 'cast handstand', 'kind': 'skill'})
        self.assertEqual(response.context['selected']['count'], 3)
        self.assertEqual(len(response.context['sections']), 3)
        self.assertIn(normalized.pk, [v.pk for v in response.context['page_obj']])
        self.assertNotContains(response, 'Beam ·')
        self.assertEqual(self.client.get(self.url(), {'event': 'not-an-event'}).status_code, 404)

    def test_full_routine_without_skill_label_can_be_compared_but_unlabelled_skills_cannot(self):
        self.create(skill_name='', event='floor', video_type='routine')
        self.create(skill_name='', event='floor', video_type='mock_meet')
        self.create(skill_name='', event='bars')
        self.create(skill_name='', event='bars')
        self.login()
        response = self.client.get(self.url(), {'event': 'floor', 'skill': '', 'kind': 'routine'})
        self.assertEqual(response.context['selected']['label'], 'Full routine')
        self.assertIsNotNone(response.context['comparison'])
        response = self.client.get(self.url(), {'event': 'bars', 'skill': '', 'kind': 'skill'})
        self.assertIsNone(response.context['comparison'])
        self.assertNotContains(response, 'id="play-both"')

    def test_parent_only_sees_published_parent_videos_and_no_coach_notes(self):
        for visibility in ('coaches', 'private', 'athlete'):
            self.create(title='Hidden ' + visibility, visibility=visibility)
        self.first.notes = 'SECRET PRIVATE COACH NOTE'
        self.first.save()
        self.login(self.parent)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_video_count'], 2)
        self.assertNotContains(response, 'Hidden')
        self.assertNotContains(response, 'SECRET PRIVATE COACH NOTE')
        self.assertNotContains(response, 'Open full comparison')
        self.assertNotContains(response, 'Open video &amp; review')
        self.assertEqual(self.client.get(self.url(self.other_child)).status_code, 404)
        self.link.approved = False
        self.link.save()
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_parent_gym_boundary_and_membership_revocation(self):
        GymMembership.objects.create(gym=self.foreign_gym, user=self.athlete, role='athlete')
        hidden = self.create(title='Foreign gym cast', gym=self.foreign_gym)
        self.login(self.parent)
        response = self.client.get(self.url())
        self.assertNotContains(response, hidden.title)
        GymMembership.objects.filter(gym=self.gym, user=self.athlete).update(is_active=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_athlete_only_sees_own_shared_videos_including_tagged_clips(self):
        tagged = self.create(primary_athlete=self.other_child, visibility='athlete', title='Group cast')
        tagged.tagged_athletes.add(self.athlete)
        self.create(title='Coach-only cast', visibility='coaches')
        self.login(self.athlete)
        response = self.client.get(self.url())
        self.assertEqual(response.context['total_video_count'], 3)
        self.assertContains(response, 'Tagged athlete · shared clip')
        self.assertNotContains(response, 'Coach-only cast')
        self.assertEqual(self.client.get(self.url(self.other_child)).status_code, 404)

    def test_coach_private_group_foreign_gym_and_ambiguous_membership_access(self):
        foreign_child = get_user_model().objects.create_user('foreign-child', role='athlete')
        GymMembership.objects.create(gym=self.foreign_gym, user=foreign_child, role='athlete')
        self.create(primary_athlete=foreign_child, gym=self.foreign_gym, title='Foreign attempt')
        private = self.create(uploaded_by=self.head, visibility='private', title='Head private cast')
        group = TrainingGroup.objects.create(name='Other coaching group', gym=self.gym)
        grouped = self.create(uploaded_by=self.head, training_group=group, title='Other group cast')
        self.login()
        response = self.client.get(self.url())
        self.assertEqual(response.context['total_video_count'], 2)
        self.assertNotContains(response, private.title)
        self.assertNotContains(response, grouped.title)
        self.assertEqual(self.client.get(self.url(foreign_child)).status_code, 404)
        GymMembership.objects.create(gym=self.foreign_gym, user=self.coach, role='coach')
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_only_ready_real_attempts_count_no_examples_or_archived_videos(self):
        for extra in ({'status': 'archived'}, {'status': 'uploading'}, {'status': 'failed'},
                      {'is_skill_library_video': True}, {'is_coaching_example': True}, {'video_file': ''}):
            self.create(**extra)
        self.login()
        response = self.client.get(self.url())
        self.assertEqual(response.context['total_video_count'], 2)

    def test_compare_selected_attempt_requires_same_accessible_group(self):
        middle = self.create(recorded_at=self.now - timedelta(days=20))
        wrong_event = self.create(event='floor')
        private = self.create(uploaded_by=self.head, visibility='private')
        self.login()
        filters = dict(event='bars', skill='cast handstand', kind='skill', compare=str(middle.pk))
        response = self.client.get(self.url(), filters)
        self.assertEqual(response.context['comparison']['current'].pk, middle.pk)
        self.assertFalse(response.context['comparison']['is_latest'])
        for invalid in (str(wrong_event.pk), str(private.pk), 'not-an-id', '999999'):
            self.assertEqual(self.client.get(self.url(), dict(filters, compare=invalid)).status_code, 404)

    def test_full_range_comparison_is_preserved_on_paginated_history(self):
        for index in range(15):
            self.create(recorded_at=self.now - timedelta(days=45-index), title=f'Middle {index}')
        self.login()
        response = self.client.get(self.url(), {'page': '2'})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['page_obj']), 5)
        self.assertEqual(response.context['comparison']['first'].pk, self.first.pk)
        self.assertEqual(response.context['comparison']['current'].pk, self.latest.pk)

    def test_entry_points_and_both_legacy_timeline_urls_work(self):
        self.login()
        for page in ('dashboard', 'video_list'):
            self.assertContains(self.client.get(reverse('video_library:' + page)), 'Athlete Progress')
        self.assertEqual(self.client.get(reverse('video_library:athlete_video_timeline',
                                                args=[self.athlete.pk])).status_code, 200)
        index = self.client.get(reverse('video_library:video_progress'))
        self.assertContains(index, self.url())
        self.login(self.parent)
        self.assertContains(self.client.get(reverse('video_library:family_library')), self.url())
        index = self.client.get(reverse('video_library:video_progress'))
        self.assertContains(index, self.athlete.username)
        self.assertNotContains(index, self.other_child.username)

    def test_assigned_athlete_without_video_has_clear_empty_state(self):
        CoachAthleteAssignment.objects.create(coach=self.coach, athlete=self.other_child)
        self.login()
        response = self.client.get(self.url(self.other_child))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No videos here yet')
        self.assertNotContains(response, 'id="play-both"')

    def test_coach_group_roster_is_available_even_before_upload(self):
        group = TrainingGroup.objects.create(name='My training group', gym=self.gym)
        group.coaches.add(self.coach)
        group.athletes.add(self.other_child)
        self.login()
        response = self.client.get(self.url(self.other_child))
        self.assertEqual(response.status_code, 200)
        group.is_active = False
        group.save()
        self.assertEqual(self.client.get(self.url(self.other_child)).status_code, 404)

    def test_anonymous_and_director_cannot_open_timeline(self):
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        director = get_user_model().objects.create_user('progress-director', role='director')
        self.login(director)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
