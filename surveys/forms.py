from django import forms
from skill_tracker.models import Assignment
from gyms.tenant import single_active_gym_id
from .models import DailySurvey


class DailySurveyForm(forms.ModelForm):
    energy = forms.TypedChoiceField(coerce=int, choices=[(5, 'Lots'), (3, 'Some'), (1, 'Very little')], widget=forms.RadioSelect)
    help_skill = forms.ModelChoiceField(queryset=Assignment.objects.none(), required=False, empty_label='No specific skill', label='Or choose one of your skills')

    class Meta:
        model = DailySurvey
        fields = ['energy', 'sleep_quality', 'body_feeling', 'practice_feeling', 'help_event',
                  'help_skill', 'coach_talk', 'soreness_area', 'told_coach', 'worry_about', 'help_kind']
        widgets = {name: forms.RadioSelect for name in ['sleep_quality', 'body_feeling',
                   'practice_feeling', 'help_event', 'coach_talk', 'told_coach', 'worry_about', 'help_kind']}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['sleep_quality', 'body_feeling', 'practice_feeling', 'help_event', 'coach_talk']:
            self.fields[name].required = True
            self.fields[name].choices = [(k,v) for k,v in self.fields[name].choices if k]
        self.fields['soreness_area'] = forms.ChoiceField(required=False, label='Where?', choices=[('', 'Choose an area'), ('head', 'Head / neck'), ('shoulder', 'Shoulder / arm'), ('wrist', 'Wrist / hand'), ('back', 'Back'), ('hip', 'Hip / thigh'), ('knee', 'Knee'), ('ankle', 'Ankle / foot'), ('multiple', 'More than one place'), ('private', "I'd rather tell my coach")])
        if user:
            self.fields['help_skill'].queryset = Assignment.objects.filter(athlete=user, is_active=True,
                skill__gym_id=single_active_gym_id(user, ['athlete'])).select_related('skill')
            self.fields['help_skill'].label_from_instance = lambda a: f'{a.skill.get_event_display()} — {a.skill.name}'

    def clean(self):
        data = super().clean()
        body = data.get('body_feeling')
        if body not in ('sore', 'pain'):
            data['soreness_area'] = ''
        if body in ('pain', 'sick'):
            if not data.get('told_coach'):
                self.add_error('told_coach', 'Please choose an answer.')
        else:
            data['told_coach'] = ''
        if data.get('practice_feeling') != 'nervous':
            data['worry_about'] = ''
        skill = data.get('help_skill')
        event = data.get('help_event')
        if skill and event not in ('none', '', None, skill.skill.event):
            self.add_error('help_skill', 'Choose a skill for the selected event, or select Nothing specific.')
        if not skill and event in ('none', '', None):
            data['help_kind'] = ''
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.checkin_version = 2
        # New questions are not fabricated numeric soreness/stress or sleep-hour measurements.
        instance.soreness = None
        instance.stress = None
        if commit:
            instance.save()
        return instance
