from datetime import date, time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from gyms.models import Gym, GymMembership, TrainingGroup
from .forms import GroupScheduleForm
from .models import GroupSchedule


class ScheduleTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='North')
        self.other = Gym.objects.create(name='South')
        self.group = TrainingGroup.objects.create(gym=self.gym, name='Level 3')
        self.foreign = TrainingGroup.objects.create(gym=self.other, name='Foreign group')
        self.director = get_user_model().objects.create_user(username='director',role='director')
        GymMembership.objects.create(gym=self.gym,user=self.director,role='director',is_active=True)
        self.data={'group':self.group.pk,'weekdays':['0','2'],'start_date':'2026-10-01',
                   'end_date':'2026-12-31','start_time':'16:00','end_time':'19:00','is_active':'on'}

    def form(self, **changes):
        return GroupScheduleForm(dict(self.data, **changes),gym_id=self.gym.pk)

    def test_days_and_season_boundaries(self):
        form=self.form();self.assertTrue(form.is_valid(),form.errors)
        s=form.save()
        self.assertTrue(s.occurs_on(date(2026,10,5)))
        self.assertTrue(s.occurs_on(date(2026,10,7)))
        self.assertFalse(s.occurs_on(date(2026,10,6)))
        self.assertFalse(s.occurs_on(date(2026,9,30)))
        self.assertFalse(s.occurs_on(date(2027,1,4)))
        s.is_active=False
        self.assertFalse(s.occurs_on(date(2026,10,5)))

    def test_invalid_dates_times_and_days(self):
        for values in [{'end_time':'15:00'},{'end_date':'2026-09-01'},
                       {'weekdays':[]},{'weekdays':['9']},
                       {'start_date':'2026-10-01','end_date':'2026-10-01'}]:
            self.assertFalse(self.form(**values).is_valid(),values)

    def test_overlapping_same_group_rejected_adjacent_allowed(self):
        f=self.form();self.assertTrue(f.is_valid());f.save()
        self.assertFalse(self.form(start_time='18:00',end_time='20:00').is_valid())
        self.assertTrue(self.form(start_time='19:00',end_time='20:00').is_valid())
        self.assertTrue(self.form(weekdays=['1']).is_valid())

    def test_post_creates_and_pause_and_edit(self):
        self.client.force_login(self.director)
        response=self.client.post(reverse('group_schedules'),self.data)
        self.assertEqual(response.status_code,302)
        s=GroupSchedule.objects.get()
        paused=dict(self.data);paused.pop('is_active')
        self.assertEqual(self.client.post(reverse('group_schedule_edit',args=[s.pk]),paused).status_code,302)
        s.refresh_from_db();self.assertFalse(s.is_active)
        self.assertEqual(GroupSchedule.objects.count(),1)

    def test_foreign_group_and_foreign_schedule_denied(self):
        self.assertFalse(self.form(group=self.foreign.pk).is_valid())
        self.client.force_login(self.director)
        foreign=GroupSchedule.objects.create(group=self.foreign,weekdays=[0],start_date=date(2026,10,1),end_date=date(2026,12,31),start_time=time(16),end_time=time(19))
        for method in [self.client.get,self.client.post]:
            self.assertEqual(method(reverse('group_schedule_edit',args=[foreign.pk])).status_code,404)
        with patch('gym_scheduling.views.render',return_value=HttpResponse()) as render:
            self.client.post(reverse('group_schedules'),dict(self.data,group=self.foreign.pk))
            self.assertTrue(render.call_args.args[2]['form'].errors)
        self.assertEqual(GroupSchedule.objects.count(),1)

    def test_non_director_and_inactive_membership_denied(self):
        self.client.force_login(self.director)
        GymMembership.objects.filter(user=self.director).update(is_active=False)
        self.assertEqual(self.client.get(reverse('group_schedules')).status_code,403)
        self.director.role='coach';self.director.save()
        GymMembership.objects.filter(user=self.director).update(is_active=True)
        self.assertEqual(self.client.post(reverse('group_schedules'),self.data).status_code,403)

    def test_list_is_scoped(self):
        self.client.force_login(self.director)
        GroupSchedule.objects.create(group=self.foreign,weekdays=[0],start_date=date(2026,10,1),end_date=date(2026,12,31),start_time=time(16),end_time=time(19))
        with patch('gym_scheduling.views.render',return_value=HttpResponse()) as render:
            self.client.get(reverse('group_schedules'))
            self.assertEqual(list(render.call_args.args[2]['schedules']),[])
            self.assertEqual(list(render.call_args.args[2]['form'].fields['group'].queryset),[self.group])
