from django import forms
from gyms.models import TrainingGroup
from .models import GroupSchedule, WEEKDAYS


class GroupScheduleForm(forms.ModelForm):
    weekdays = forms.TypedMultipleChoiceField(
        choices=WEEKDAYS, coerce=int, widget=forms.CheckboxSelectMultiple,
        label='Training days',
    )

    class Meta:
        model = GroupSchedule
        fields = ['group', 'weekdays', 'start_date', 'end_date', 'start_time', 'end_time', 'is_active']
        labels = {'group': 'Training group', 'start_date': 'Season starts',
                  'end_date': 'Season ends', 'is_active': 'Schedule active'}
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }

    def __init__(self, *args, gym_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].queryset = TrainingGroup.objects.filter(gym_id=gym_id, is_active=True)
        for name, field in self.fields.items():
            if name == 'weekdays':
                continue
            field.widget.attrs['class'] = ('form-check-input' if name == 'is_active'
                                           else 'form-select' if name == 'group' else 'form-control')


class ScheduleExceptionForm(forms.Form):
    date = forms.DateField(label='Session date', widget=forms.DateInput(attrs={'type': 'date'}))
    action = forms.ChoiceField(choices=[('cancel', 'Cancel this session'), ('change', 'Change hours for this date')])
    start_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'},format='%H:%M'))
    end_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'},format='%H:%M'))
    note = forms.CharField(required=False, max_length=240, label='Reason or note', widget=forms.TextInput())

    def __init__(self, *args, schedule, **kwargs):
        super().__init__(*args, **kwargs)
        self.schedule = schedule
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-select' if name == 'action' else 'form-control'
        self.fields['date'].widget.attrs.update(min=schedule.start_date.isoformat(),max=schedule.end_date.isoformat())

    def clean(self):
        from .models import ScheduleException
        data = super().clean()
        if self.errors:
            return data
        candidate = ScheduleException(schedule=self.schedule, **data)
        candidate.clean()
        data['start_time'], data['end_time'] = candidate.start_time, candidate.end_time
        return data
