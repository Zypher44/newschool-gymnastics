from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from athletes.models import AthleteProfile, AttendanceRecord
from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from communications.models import Notification
from .models import ParentAthleteLink, PracticeAbsenceNotice


class ParentUpdatesTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Family Gym')
        self.other_gym = Gym.objects.create(name='Other Gym')
        self.parent = self.person('parent', 'parent')
        self.child = self.person('Alex', 'athlete')
        self.second = self.person('Jamie', 'athlete')
        self.coach = self.person('coach', 'coach')
        self.foreign = self.person('Outsider', 'athlete', self.other_gym)
        for child in [self.child, self.second]:
            ParentAthleteLink.objects.create(parent=self.parent, athlete=child, approved=True)
        self.group = TrainingGroup.objects.create(gym=self.gym, name='Training')
        TrainingGroupAthlete.objects.create(group=self.group, athlete=self.child)
        TrainingGroupCoach.objects.create(group=self.group, coach=self.coach)
        self.client.force_login(self.parent)

    def person(self, name, role, gym=None):
        user = get_user_model().objects.create_user(username=name, first_name=name, role=role)
        GymMembership.objects.create(user=user, gym=gym or self.gym, role=role)
        return user

    def test_connect_dropdown_limited_to_gym_and_still_needs_dob_approval(self):
        extra = self.person('Unlinked', 'athlete')
        AthleteProfile.objects.create(user=extra, date_of_birth=date(2015,1,2))
        url = reverse('connect_athlete')
        response = self.client.get(url)
        ids = set(response.context['form'].fields['athlete'].queryset.values_list('pk', flat=True))
        self.assertIn(extra.pk, ids); self.assertNotIn(self.foreign.pk, ids)
        for changes in [{'athlete': self.foreign.pk}, {'date_of_birth': '2014-01-02'}]:
            self.assertEqual(self.client.post(url, {'athlete': extra.pk, 'date_of_birth': '2015-01-02', 'relationship':'Guardian', **changes}).status_code, 200)
        self.assertFalse(ParentAthleteLink.objects.filter(athlete=extra).exists())
        self.assertEqual(self.client.post(url, {'athlete':extra.pk,'date_of_birth':'2015-01-02','relationship':'Guardian'}).status_code,302)
        self.assertFalse(ParentAthleteLink.objects.get(athlete=extra).approved)

    def test_switch_persists_across_reports_passport_and_journal(self):
        response = self.client.post(reverse('switch_child'), {'athlete':self.second.pk, 'next':reverse('practice_focus:family_progress')})
        self.assertEqual(response.status_code,302)
        response = self.client.get(reverse('practice_focus:family_progress'))
        self.assertEqual(response.context['athlete'],self.second)
        response = self.client.get(reverse('practice_focus:family_passport'))
        self.assertEqual(response.context['athlete'],self.second)
        response = self.client.get(reverse('practice_focus:journal_history'))
        self.assertEqual(response.context['selected_athlete'],str(self.second.pk))
        self.assertEqual(self.client.post(reverse('switch_child'),{'athlete':self.foreign.pk}).status_code,404)
        self.assertEqual(self.client.get(reverse('practice_focus:family_progress'),{'athlete':self.foreign.pk}).status_code,404)
        ParentAthleteLink.objects.filter(parent=self.parent,athlete=self.second).update(approved=False)
        response = self.client.get(reverse('practice_focus:family_progress'))
        self.assertEqual(response.context['athlete'],self.child)

    def test_absence_notifies_assigned_staff_and_never_changes_attendance(self):
        day = timezone.localdate()
        data = {'athlete':self.child.pk,'practice_date':day.isoformat(),'status':'late','expected_arrival':'17:30','note':'School appointment','version':0}
        response = self.client.post(reverse('parent_absence'),data)
        self.assertEqual(response.status_code,302)
        notice=PracticeAbsenceNotice.objects.get()
        self.assertEqual(notice.status,'late')
        self.assertFalse(AttendanceRecord.objects.exists())
        self.assertTrue(Notification.objects.filter(recipient=self.coach,notification_type='attendance').exists())
        self.assertEqual(self.client.post(reverse('parent_absence'),data).status_code,200)
        notice.refresh_from_db();self.assertEqual(notice.version,1)
        response=self.client.get(reverse('gym_calendar'))
        self.assertContains(response,'School appointment')
        self.client.post(reverse('parent_absence'),{**data,'status':'cancelled','version':1})
        notice.refresh_from_db();self.assertEqual(notice.status,'cancelled')
        self.assertEqual(notice.note,'')

    def test_absence_rejects_unlinked_past_and_wrong_group_events(self):
        from coaches.models import TeamEvent
        group=TrainingGroup.objects.create(gym=self.gym,name='Other team')
        event=TeamEvent.objects.create(gym=self.gym,title='Other team practice',event_date=timezone.localdate(),audience='all',training_group=group)
        data={'athlete':self.child.pk,'practice_date':timezone.localdate().isoformat(),'status':'absent','version':0}
        for changes in [{'athlete':self.foreign.pk},{'practice_date':(timezone.localdate()-timedelta(days=1)).isoformat()},{'event':event.pk}]:
            self.assertEqual(self.client.post(reverse('parent_absence'),{**data,**changes}).status_code,200)
        self.assertFalse(PracticeAbsenceNotice.objects.exists())

    def test_navigation_renders_with_icons_and_csrf_protected_switch(self):
        response=self.client.get(reverse('parent_dashboard'))
        self.assertContains(response,'My Child’s Progress')
        self.assertNotContains(response, 'id="family-child"')
        client=Client(enforce_csrf_checks=True);client.force_login(self.parent)
        self.assertEqual(client.post(reverse('switch_child'),{'athlete':self.child.pk}).status_code,403)

    def test_child_switcher_only_in_settings_and_saves_across_portal(self):
        settings = self.client.get(reverse('account_settings'))
        self.assertContains(settings, 'id="family-child"')
        self.assertContains(settings, 'Save child view')
        self.assertContains(settings, f'value="{self.second.pk}"')
        self.assertNotContains(settings, f'value="{self.foreign.pk}"')
        response = self.client.post(reverse('switch_child'), {'athlete': self.second.pk, 'next': 'https://example.com'})
        self.assertRedirects(response, reverse('account_settings') + '#family-view')
        self.assertEqual(self.client.session['selected_child'], self.second.pk)
        settings = self.client.get(reverse('account_settings'))
        self.assertContains(settings, f'<option value="{self.second.pk}" selected>Jamie</option>', html=True)
        for name in ['parent_dashboard', 'parent_conditioning_history', 'practice_focus:family_progress',
                     'practice_focus:family_passport', 'practice_focus:journal_history', 'gym_calendar']:
            page = self.client.get(reverse(name))
            for marker in ['id="family-child"', 'id="family-athlete"', 'id="passport-athlete"',
                           'Switch Athlete', 'name="athlete"']:
                self.assertNotContains(page, marker)
        self.assertEqual(self.client.get(reverse('practice_focus:family_progress')).context['athlete'], self.second)

    def test_settings_hides_unapproved_children_and_handles_empty_connections(self):
        ParentAthleteLink.objects.filter(parent=self.parent).update(approved=False)
        settings = self.client.get(reverse('account_settings'))
        self.assertContains(settings, 'No approved child connections yet')
        self.assertNotContains(settings, 'id="family-child"')
        self.assertEqual(self.client.post(reverse('switch_child'), {'athlete': self.second.pk}).status_code, 404)
        self.client.force_login(self.coach)
        self.assertNotContains(self.client.get(reverse('account_settings')), 'id="family-view"')
