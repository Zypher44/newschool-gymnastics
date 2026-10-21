from django import forms
from django.core.exceptions import ValidationError
from .models import EVENTS


class PersonalPlanForm(forms.Form):
    title = forms.CharField(max_length=150, initial='Daily practice')
    level = forms.CharField(max_length=100, required=False, label='Athlete level / pathway')
    focus = forms.CharField(max_length=250, required=False, label='Main focus')
    notes = forms.CharField(max_length=3000, required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Notes shown to athlete')
    version = forms.CharField(required=False, widget=forms.HiddenInput)
    current_version = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, skills, **kwargs):
        super().__init__(*args, **kwargs)
        self.skills = skills
        for event, label in EVENTS:
            self.fields[event + '_minutes'] = forms.IntegerField(min_value=0, max_value=240, required=False, label='Minutes')
            self.fields[event + '_routines'] = forms.IntegerField(min_value=0, max_value=100, required=False, label='Routine target')
            self.fields[event + '_pressure'] = forms.IntegerField(min_value=0, max_value=100, required=False, label='Pressure set target')
            self.fields[event + '_cue'] = forms.CharField(max_length=1000, required=False, label='Event focus', widget=forms.Textarea(attrs={'rows': 2}))
        for skill in skills:
            self.fields['skill_' + str(skill.pk)] = forms.BooleanField(required=False, label=skill.name)
            self.fields['target_' + str(skill.pk)] = forms.IntegerField(min_value=0, max_value=200, required=False, label='Attempt target')
        for field in self.fields.values():
            if isinstance(field, forms.IntegerField):
                field.widget.attrs.update({'inputmode': 'numeric', 'placeholder': 'Optional'})

    def clean(self):
        data = super().clean()
        selected = {skill.pk for skill in self.skills if data.get('skill_' + str(skill.pk))}
        if self.is_bound:
            for key in self.data:
                if key.startswith('skill_') and self.data.get(key):
                    try:
                        skill_id = int(key[6:])
                    except ValueError:
                        raise ValidationError('Invalid skill selection.')
                    if skill_id not in {skill.pk for skill in self.skills}:
                        raise ValidationError('Choose skills from this gym’s catalogue.')
        for event, label in EVENTS:
            names = [skill.name for skill in self.skills if skill.event == event and skill.pk in selected]
            if len(names) > 50 or len('\n'.join(names)) > 8000:
                raise ValidationError('Choose at most 50 skills per event.')
        return data

    def plan_values(self):
        data = self.cleaned_data
        return {'title': data['title'], 'level': data['level'], 'focus': data['focus'], 'notes': data['notes'],
            'content': {event: {'minutes': data.get(event + '_minutes') or 0,
                'routines': data.get(event + '_routines') or 0,
                'pressure': data.get(event + '_pressure') or 0,
                'cue': data.get(event + '_cue', ''),
                'skills': [{'id': skill.pk, 'name': skill.name, 'target': data.get('target_' + str(skill.pk)) or 0}
                           for skill in self.skills if skill.event == event and data.get('skill_' + str(skill.pk))]}
                for event, label in EVENTS}}
