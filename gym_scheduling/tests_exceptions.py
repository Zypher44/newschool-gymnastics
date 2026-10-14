from datetime import date,time
from unittest.mock import patch
from django.http import HttpResponse
from django.test import TestCase, Client
from django.urls import reverse
from . import tests as base
from .models import GroupSchedule, ScheduleException
from .forms import ScheduleExceptionForm,GroupScheduleForm


class ExceptionTests(TestCase):
    setUp = base.ScheduleTests.setUp

    def schedule(self):
        f=GroupScheduleForm(self.data,gym_id=self.gym.pk)
        self.assertTrue(f.is_valid(),f.errors)
        return f.save()

    def test_cancel_and_restore_only_one_date(self):
        s=self.schedule();self.client.force_login(self.director)
        url=reverse('group_schedule_exceptions',args=[s.pk])
        self.assertEqual(self.client.post(url,{'date':'2026-10-05','action':'cancel','note':'Holiday'}).status_code,302)
        e=ScheduleException.objects.get();self.assertIsNone(e.start_time)
        self.assertEqual(self.client.post(url,{'date':'2026-10-05','action':'change','start_time':'17:00','end_time':'18:00'}).status_code,302)
        self.assertEqual(ScheduleException.objects.count(),1)
        e.refresh_from_db();self.assertEqual(e.start_time,time(17))
        self.assertEqual(self.client.post(url,{'operation':'restore','exception_id':e.pk}).status_code,302)
        self.assertFalse(s.exceptions.exists())
        s.refresh_from_db();self.assertEqual(s.start_time,time(16));self.assertEqual(s.weekdays,[0,2])

    def test_invalid_day_or_season_and_time_rejected(self):
        s=self.schedule()
        for data in [{'date':'2026-10-06','action':'cancel'},
                     {'date':'2027-01-04','action':'cancel'},
                     {'date':'2026-10-05','action':'change'},
                     {'date':'2026-10-05','action':'change','start_time':'19:00','end_time':'16:00'}]:
            self.assertFalse(ScheduleExceptionForm(data,schedule=s).is_valid())

    def test_changed_hours_overlap_other_series(self):
        s=self.schedule()
        other=GroupSchedule.objects.create(group=self.group,weekdays=[0],start_date=s.start_date,end_date=s.end_date,start_time=time(19),end_time=time(21))
        f=ScheduleExceptionForm({'date':'2026-10-05','action':'change','start_time':'18:00','end_time':'20:00'},schedule=s)
        self.assertFalse(f.is_valid())
        ScheduleException.objects.create(schedule=other,date=date(2026,10,5),action='cancel')
        f=ScheduleExceptionForm({'date':'2026-10-05','action':'change','start_time':'18:00','end_time':'20:00'},schedule=s)
        self.assertTrue(f.is_valid(),f.errors)

    def test_foreign_schedule_and_restore_denied(self):
        s=self.schedule();self.client.force_login(self.director)
        other=GroupSchedule.objects.create(group=self.foreign,weekdays=[0],start_date=s.start_date,end_date=s.end_date,start_time=time(16),end_time=time(19))
        e=ScheduleException.objects.create(schedule=other,date=date(2026,10,5),action='cancel')
        self.assertEqual(self.client.post(reverse('group_schedule_exceptions',args=[s.pk]),{'operation':'restore','exception_id':e.pk}).status_code,404)
        for method in [self.client.get,self.client.post]:
            self.assertEqual(method(reverse('group_schedule_exceptions',args=[other.pk])).status_code,404)
        self.assertTrue(ScheduleException.objects.filter(pk=e.pk).exists())

    def test_coach_denied_and_csrf_required(self):
        s=self.schedule();self.client.force_login(self.director)
        strict=Client(enforce_csrf_checks=True);strict.force_login(self.director)
        self.assertEqual(strict.post(reverse('group_schedule_exceptions',args=[s.pk]),{'date':'2026-10-05','action':'cancel'}).status_code,403)
        self.director.role='coach';self.director.save()
        self.assertEqual(self.client.post(reverse('group_schedule_exceptions',args=[s.pk]),{'date':'2026-10-05','action':'cancel'}).status_code,403)

    def test_restore_conflict_preserves_exception(self):
        s=self.schedule();self.client.force_login(self.director)
        e=ScheduleException.objects.create(schedule=s,date=date(2026,10,5),action='cancel')
        other=GroupSchedule.objects.create(group=self.group,weekdays=[0],start_date=s.start_date,end_date=s.end_date,start_time=time(19),end_time=time(21))
        ScheduleException.objects.create(schedule=other,date=e.date,action='change',start_time=time(17),end_time=time(18))
        self.client.post(reverse('group_schedule_exceptions',args=[s.pk]),{'operation':'restore','exception_id':e.pk})
        self.assertTrue(ScheduleException.objects.filter(pk=e.pk).exists())

    def test_series_edits_preserve_exception_integrity(self):
        s=self.schedule()
        ScheduleException.objects.create(schedule=s,date=date(2026,10,5),action='cancel')
        f=GroupScheduleForm(dict(self.data,weekdays=['2']),instance=s,gym_id=self.gym.pk)
        self.assertFalse(f.is_valid())

    def test_new_series_cannot_overlap_changed_hours(self):
        s=self.schedule()
        ScheduleException.objects.create(schedule=s,date=date(2026,10,5),action='change',start_time=time(19),end_time=time(21))
        f=GroupScheduleForm(dict(self.data,start_time='20:00',end_time='22:00'),gym_id=self.gym.pk)
        self.assertFalse(f.is_valid())

    def test_existing_exception_prefills_edit(self):
        s=self.schedule();self.client.force_login(self.director)
        ScheduleException.objects.create(schedule=s,date=date(2026,10,5),action='cancel',note='Holiday')
        with patch('gym_scheduling.views.render',return_value=HttpResponse()) as render:
            self.client.get(reverse('group_schedule_exceptions',args=[s.pk])+'?date=2026-10-05')
            self.assertEqual(render.call_args.args[2]['form'].initial['note'],'Holiday')
