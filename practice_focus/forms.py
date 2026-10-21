from django import forms


class EventSkillsForm(forms.Form):
    skills_text = forms.CharField(label='Skills currently being trained', required=False, max_length=8000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'One skill per line'}))
    training_cues = forms.CharField(label='Training cues', required=False, max_length=1000,
        help_text='Visible with the skills to the athlete and approved linked parents.',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional technique reminders or practice goals'}))
    version = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_skills_text(self):
        lines = []
        seen = set()
        for raw in self.cleaned_data['skills_text'].splitlines():
            name = raw.strip()
            if not name:
                continue
            if len(name) > 150:
                raise forms.ValidationError('Keep each skill name to 150 characters or fewer.')
            if name.casefold() not in seen:
                lines.append(name)
                seen.add(name.casefold())
        if len(lines) > 50:
            raise forms.ValidationError('Enter up to 50 skills per event.')
        return '\n'.join(lines)

    def clean_training_cues(self):
        return self.cleaned_data['training_cues'].strip()
