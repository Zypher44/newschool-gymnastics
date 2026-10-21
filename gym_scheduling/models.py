from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models

WEEKDAYS = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
            (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]


class GroupSchedule(models.Model):
    group = models.ForeignKey('gyms.TrainingGroup', on_delete=models.CASCADE,
                              related_name='recurring_schedules')
    weekdays = models.JSONField(default=list)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['group__name', 'start_date', 'start_time']
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')),
                                   name='schedule_dates_in_order'),
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F('start_time')),
                                   name='schedule_times_in_order'),
        ]

    @property
    def weekday_labels(self):
        return ', '.join(label for number, label in WEEKDAYS if number in self.weekdays)

    def occurs_on(self, day):
        return (self.is_active and self.start_date <= day <= self.end_date
                and day.weekday() in self.weekdays)

    def clean(self):
        super().clean()
        if (not isinstance(self.weekdays, list) or not self.weekdays
                or any(type(n) is not int or not 0 <= n <= 6 for n in self.weekdays)
                or len(set(self.weekdays)) != len(self.weekdays)):
            raise ValidationError({'weekdays': 'Select at least one valid weekday.'})
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({'end_date': 'End date must be on or after start date.'})
            if not any((self.start_date + timedelta(days=i)).weekday() in self.weekdays
                       for i in range(min(7, (self.end_date - self.start_date).days + 1))):
                raise ValidationError({'weekdays': 'No selected weekday falls within these dates.'})
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time on the same day.'})
        if self.pk:
            exceptions = list(self.exceptions.all())
            original = GroupSchedule.objects.get(pk=self.pk)
            if exceptions and original.group_id != self.group_id:
                raise ValidationError('Restore single-day exceptions before changing this series to another group.')
            for exception in exceptions:
                if (self.start_date and self.end_date and not (
                        self.start_date <= exception.date <= self.end_date
                        and exception.date.weekday() in self.weekdays)):
                    raise ValidationError('Restore exceptions outside the new season or weekdays before changing this series.')
                if self.is_active and exception.action == 'change':
                    check_session_conflict(self, exception.date, exception.start_time, exception.end_time)
        if not (self.group_id and self.start_date and self.end_date and self.start_time and self.end_time and self.is_active):
            return
        changed_sessions = ScheduleException.objects.filter(
            schedule__group_id=self.group_id, schedule__is_active=True,
            date__range=(self.start_date, self.end_date), action='change',
        ).exclude(schedule_id=self.pk)
        for exception in changed_sessions:
            if (exception.date.weekday() in self.weekdays
                    and self.start_time < exception.end_time and self.end_time > exception.start_time):
                raise ValidationError('These hours overlap a single-day change for this group. Adjust that exception first.')
        others = GroupSchedule.objects.filter(
            group_id=self.group_id, is_active=True, start_date__lte=self.end_date,
            end_date__gte=self.start_date, start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        for other in others:
            first, last = max(self.start_date, other.start_date), min(self.end_date, other.end_date)
            if any((first + timedelta(days=i)).weekday() in set(self.weekdays) & set(other.weekdays)
                   for i in range(min(7, (last - first).days + 1))):
                raise ValidationError('This group already has a recurring session overlapping these dates and times.')


class ScheduleException(models.Model):
    ACTIONS = [('cancel', 'Cancel this session'), ('change', 'Change hours for this date')]
    schedule = models.ForeignKey(GroupSchedule, on_delete=models.CASCADE, related_name='exceptions')
    date = models.DateField()
    action = models.CharField(max_length=10, choices=ACTIONS)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(fields=['schedule', 'date'], name='one_exception_per_session'),
            models.CheckConstraint(
                condition=(models.Q(action='cancel', start_time__isnull=True, end_time__isnull=True)
                           | models.Q(action='change', start_time__isnull=False, end_time__isnull=False,
                                      end_time__gt=models.F('start_time'))),
                name='valid_exception_hours',
            ),
        ]

    def clean(self):
        super().clean()
        if not self.schedule_id or not self.date:
            return
        schedule = self.schedule
        if not (schedule.start_date <= self.date <= schedule.end_date
                and self.date.weekday() in schedule.weekdays):
            raise ValidationError({'date': 'Choose a scheduled training day within this series.'})
        if self.action == 'cancel':
            self.start_time = self.end_time = None
        elif self.action == 'change':
            if not self.start_time or not self.end_time or self.end_time <= self.start_time:
                raise ValidationError('Enter a start and end time, ending later on the same day.')
            check_session_conflict(schedule, self.date, self.start_time, self.end_time)
        else:
            raise ValidationError({'action': 'Choose cancellation or changed hours.'})


def check_session_conflict(schedule, day, start, end):
    """Use each other recurring series' effective hours on this date."""
    if not schedule.is_active:
        return
    others = GroupSchedule.objects.filter(
        group_id=schedule.group_id, is_active=True,
        start_date__lte=day, end_date__gte=day,
    ).exclude(pk=schedule.pk).prefetch_related('exceptions')
    for other in others:
        if not other.occurs_on(day):
            continue
        override = next((e for e in other.exceptions.all() if e.date == day), None)
        if override and override.action == 'cancel':
            continue
        left, right = ((override.start_time, override.end_time) if override
                       else (other.start_time, other.end_time))
        if start < right and end > left:
            raise ValidationError('These hours overlap another recurring session for this training group on this date.')
