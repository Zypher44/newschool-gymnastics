from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from athletes.models import AttendanceRecord
from coaches.models import CoachAthleteAssignment
from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from parents_portal.models import ParentAthleteLink
from skill_tracker.models import SkillResult
from practice_focus.models import AthleteJournalEntry, PassportStamp, TrackedResult


class AthleteJournalTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Journal gym')
        self.other_gym = Gym.objects.create(name='Other journal gym')
        self.child = self.person('Mia', 'athlete')
        self.peer = self.person('Peer', 'athlete')
        self.foreign = self.person('Foreign', 'athlete', self.other_gym)
        self.head = self.person('Head', 'head_coach')
        self.coach = self.person('Coach', 'coach')
        self.unassigned = self.person('Unassigned', 'coach')
        self.parent = self.person('Parent', 'parent')
        self.pending_parent = self.person('Pending', 'parent')
        self.director = self.person('Director', 'director')
        self.link = ParentAthleteLink.objects.create(parent=self.parent, athlete=self.child, approved=True)
        ParentAthleteLink.objects.create(parent=self.pending_parent, athlete=self.child, approved=False)
        CoachAthleteAssignment.objects.create(coach=self.coach, athlete=self.child)
        self.today = timezone.localdate()
        self.history = reverse('practice_focus:journal_history')
        self.new = reverse('practice_focus:journal_new')
        self.client.force_login(self.child)

    def person(self, name, role, gym=None):
        user = get_user_model().objects.create_user(username=name, first_name=name, role=role)
        GymMembership.objects.create(gym=gym or self.gym, user=user, role=role)
        return user

    def entry(self, **extra):
        return AthleteJournalEntry.objects.create(**{'gym': self.gym, 'athlete': self.child,
            'entry_date': self.today, 'win': 'PRIVATE JOURNAL WIN', **extra})

    def detail(self, entry):
        return reverse('practice_focus:journal_detail', args=[entry.pk])

    def edit(self, entry):
        return reverse('practice_focus:journal_edit', args=[entry.pk])

    def post(self, url=None, **extra):
        return self.client.post(url or self.new, {'entry_date': self.today.isoformat(),
            'mood': 'great', 'win': 'I used my correction', 'challenge': '',
            'next_focus': 'Keep my arms straight', 'version': 0, **extra})

    def test_reading_and_opening_new_form_do_not_create_entries(self):
        for url in (self.history, self.new):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertFalse(AthleteJournalEntry.objects.exists())

    def test_save_defaults_private_and_records_author_gym_and_date(self):
        result = self.post(athlete=self.peer.pk, gym=self.other_gym.pk)
        entry = AthleteJournalEntry.objects.get()
        self.assertRedirects(result, self.detail(entry))
        self.assertEqual(entry.athlete, self.child)
        self.assertEqual(entry.gym, self.gym)
        self.assertEqual(entry.entry_date, self.today)
        self.assertFalse(entry.share_with_coaches)
        self.assertFalse(entry.share_with_parents)
        self.assertEqual(entry.version, 1)
        self.assertIsNotNone(entry.created_at)

    def test_mood_only_entry_is_allowed_for_younger_children(self):
        response = self.post(win='', next_focus='', mood='okay')
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(self.detail(AthleteJournalEntry.objects.get())), 'Okay')

    def test_blank_future_invalid_mood_and_overlong_answers_do_not_save(self):
        cases = [{'mood': '', 'win': '', 'next_focus': ''},
                 {'entry_date': (self.today + timedelta(days=1)).isoformat()},
                 {'entry_date': 'not-a-date'}, {'mood': 'not-a-mood'}, {'win': 'a' * 1501}]
        for case in cases:
            response = self.post(**case)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(AthleteJournalEntry.objects.exists())

    def test_backdated_entries_can_be_saved_and_reread(self):
        earlier = self.today - timedelta(days=365)
        response = self.post(entry_date=earlier.isoformat())
        entry = AthleteJournalEntry.objects.get()
        self.assertRedirects(response, self.detail(entry))
        self.assertContains(self.client.get(self.history), earlier.strftime('%Y'))
        self.assertEqual(entry.entry_date, earlier)

    def test_today_button_and_specific_date_resume_existing_entry(self):
        current = self.entry()
        old = self.entry(entry_date=self.today - timedelta(days=9))
        self.assertRedirects(self.client.get(self.new), self.edit(current))
        self.assertRedirects(self.client.get(self.new, {'date': old.entry_date.isoformat()}), self.edit(old))
        self.assertEqual(self.client.get(self.new, {'date': 'bad'}).status_code, 404)
        self.assertEqual(self.client.get(self.new, {'date': (self.today + timedelta(days=1)).isoformat()}).status_code, 404)

    def test_second_new_post_cannot_duplicate_or_overwrite_saved_date(self):
        self.post()
        entry = AthleteJournalEntry.objects.get()
        response = self.post(win='SECOND UNSAVED DRAFT')
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'SECOND UNSAVED DRAFT', status_code=409)
        entry.refresh_from_db()
        self.assertEqual(entry.win, 'I used my correction')
        self.assertEqual(AthleteJournalEntry.objects.count(), 1)

    def test_edit_keeps_original_date_and_updates_content_and_version(self):
        entry = self.entry(entry_date=self.today - timedelta(days=6))
        old_date, created = entry.entry_date, entry.created_at
        response = self.post(self.edit(entry), version=entry.version,
            win='I remembered the correction', share_with_coaches='on')
        self.assertRedirects(response, self.detail(entry))
        entry.refresh_from_db()
        self.assertEqual(entry.entry_date, old_date)
        self.assertEqual(entry.created_at, created)
        self.assertEqual(entry.version, 2)
        self.assertTrue(entry.share_with_coaches)

    def test_stale_edit_keeps_saved_entry_and_preserves_posted_answers(self):
        entry = self.entry()
        self.post(self.edit(entry), version=1, win='First tab saved')
        response = self.post(self.edit(entry), version=1, win='Second tab draft')
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'Second tab draft', status_code=409)
        entry.refresh_from_db()
        self.assertEqual(entry.win, 'First tab saved')
        self.assertEqual(entry.version, 2)

    def test_private_entries_are_hidden_from_every_other_role(self):
        entry = self.entry()
        for user in (self.peer, self.head, self.coach, self.parent, self.pending_parent):
            self.client.force_login(user)
            self.assertNotContains(self.client.get(self.history), entry.win)
            self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)

    def test_coach_sharing_respects_direct_and_group_assignments(self):
        entry = self.entry(share_with_coaches=True)
        for user in (self.head, self.coach):
            self.client.force_login(user)
            self.assertContains(self.client.get(self.detail(entry)), entry.win)
        self.client.force_login(self.unassigned)
        self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)
        group = TrainingGroup.objects.create(gym=self.gym, name='Journal group')
        TrainingGroupAthlete.objects.create(group=group, athlete=self.child)
        TrainingGroupCoach.objects.create(group=group, coach=self.unassigned)
        self.assertContains(self.client.get(self.detail(entry)), entry.win)
        TrainingGroupAthlete.objects.filter(group=group, athlete=self.child).update(is_active=False)
        self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)

    def test_parent_sharing_requires_approved_link_and_does_not_share_to_coaches(self):
        entry = self.entry(share_with_parents=True)
        self.client.force_login(self.parent)
        self.assertContains(self.client.get(self.detail(entry)), entry.win)
        for user in (self.pending_parent, self.coach, self.head):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)
        self.link.approved = False; self.link.save()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)

    def test_unsharing_immediately_removes_viewer_access(self):
        entry = self.entry(share_with_coaches=True, share_with_parents=True)
        self.post(self.edit(entry), version=1)
        for user in (self.coach, self.parent):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)
            self.assertNotContains(self.client.get(self.history), entry.win)

    def test_shared_viewers_cannot_create_or_edit(self):
        entry = self.entry(share_with_coaches=True, share_with_parents=True)
        for user in (self.coach, self.head, self.parent):
            self.client.force_login(user)
            self.assertNotContains(self.client.get(self.detail(entry)), 'Edit this entry')
            self.assertEqual(self.client.get(self.edit(entry)).status_code, 403)
            self.assertEqual(self.post(self.edit(entry), version=1).status_code, 403)
            self.assertEqual(self.post().status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.version, 1)

    def test_other_athlete_cannot_read_or_edit_even_when_shared(self):
        entry = self.entry(share_with_coaches=True, share_with_parents=True)
        self.client.force_login(self.peer)
        for url in (self.detail(entry), self.edit(entry)):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.post(self.edit(entry), version=1).status_code, 404)

    def test_cross_gym_shared_entries_remain_hidden(self):
        entry = self.entry(gym=self.other_gym, athlete=self.foreign,
            share_with_coaches=True, share_with_parents=True)
        # Simulate a stale imported link which normal model validation would reject.
        ParentAthleteLink.objects.bulk_create([
            ParentAthleteLink(parent=self.parent, athlete=self.foreign, approved=True)])
        for user in (self.head, self.coach, self.parent, self.child):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)
            self.assertNotContains(self.client.get(self.history), entry.win)

    def test_director_and_missing_or_ambiguous_memberships_are_denied(self):
        self.client.force_login(self.director)
        self.assertEqual(self.client.get(self.history).status_code, 403)
        self.client.force_login(self.child)
        GymMembership.objects.create(gym=self.other_gym, user=self.child, role='athlete')
        for url in (self.history, self.new): self.assertEqual(self.client.get(url).status_code, 403)
        GymMembership.objects.filter(user=self.child).update(is_active=False)
        self.assertEqual(self.post().status_code, 403)

    def test_revoked_membership_and_inactive_athlete_remove_shared_access(self):
        entry = self.entry(share_with_coaches=True, share_with_parents=True)
        self.child.is_active = False; self.child.save(update_fields=['is_active'])
        for user in (self.head, self.parent):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.detail(entry)).status_code, 404)

    def test_history_orders_by_practice_date_and_filters_inclusively(self):
        older = self.entry(entry_date=self.today - timedelta(days=40))
        middle = self.entry(entry_date=self.today - timedelta(days=8))
        newer = self.entry()
        response = self.client.get(self.history)
        self.assertEqual([entry.pk for entry in response.context['page']], [newer.pk, middle.pk, older.pk])
        response = self.client.get(self.history, {'start': middle.entry_date.isoformat(), 'end': self.today.isoformat()})
        self.assertEqual([entry.pk for entry in response.context['page']], [newer.pk, middle.pk])

    def test_invalid_history_filters_show_errors_without_leaking_entries(self):
        entry = self.entry()
        for query in ({'start': 'bad'}, {'start': self.today.isoformat(), 'end': '2000-01-01'}, {'athlete': 'bad'}):
            response = self.client.get(self.history, query)
            self.assertTrue(response.context['filter_form'].errors)
            self.assertNotContains(response, entry.win)
        self.assertEqual(self.client.get(self.history, {'athlete': self.peer.pk}).status_code, 404)

    def test_pagination_keeps_date_filters_and_shows_older_entries(self):
        for day in range(17): self.entry(entry_date=self.today - timedelta(days=day), win=f'Day {day}')
        response = self.client.get(self.history, {'start': '2000-01-01'})
        self.assertEqual(len(response.context['page']), 15)
        self.assertContains(response, 'start=2000-01-01&amp;page=2')
        older = self.client.get(self.history, {'start': '2000-01-01', 'page': 2})
        self.assertEqual(len(older.context['page']), 2)

    def test_shared_picker_does_not_reveal_private_entry_authors(self):
        self.entry(athlete=self.peer)
        self.entry(share_with_coaches=True)
        self.client.force_login(self.head)
        response = self.client.get(self.history)
        self.assertEqual(list(response.context['athletes']), [self.child])

    def test_journal_text_is_escaped_and_stays_out_of_progress_reports(self):
        entry = self.entry(win='<script>PRIVATE_JOURNAL_SCRIPT()</script>', share_with_parents=True)
        response = self.client.get(self.detail(entry))
        self.assertNotContains(response, entry.win)
        self.assertContains(response, '&lt;script&gt;')
        self.client.force_login(self.parent)
        self.assertNotContains(self.client.get(reverse('practice_focus:family_progress')), 'PRIVATE_JOURNAL_SCRIPT')

    def test_saving_journal_does_not_create_scores_attendance_or_badges(self):
        models = (SkillResult, TrackedResult, PassportStamp, AttendanceRecord)
        before = [model.objects.count() for model in models]
        self.post()
        self.assertEqual(before, [model.objects.count() for model in models])

    def test_csrf_login_and_read_only_methods(self):
        entry = self.entry()
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.child)
        self.assertEqual(csrf.post(self.new, {}).status_code, 403)
        for url in (self.history, self.detail(entry)):
            self.assertEqual(self.client.post(url, {}).status_code, 405)
        self.client.logout()
        for url in (self.history, self.new, self.detail(entry), self.edit(entry)):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_model_validation_and_database_unique_date(self):
        entry = self.entry()
        invalid = AthleteJournalEntry(gym=self.other_gym, athlete=self.child, entry_date=self.today, mood='great')
        with self.assertRaises(ValidationError): invalid.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic(): self.entry()

    def test_navigation_and_form_explain_journal_and_whole_entry_sharing(self):
        self.assertContains(self.client.get(self.history), 'My Practice Journal')
        form = self.client.get(self.new)
        self.assertContains(form, 'Sharing shows the whole entry')
        self.assertContains(form, 'Leave both boxes unticked')
        self.assertContains(form, 'My win today')
        self.assertContains(form, 'Something I found challenging')
        self.assertContains(form, 'What I want to work on next')
