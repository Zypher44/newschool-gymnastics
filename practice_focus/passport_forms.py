from django import forms
from django.utils import timezone
from .passport_catalog import SLOT_CHOICES


class StampAwardForm(forms.Form):
    slot = forms.ChoiceField(label='Choose a badge', choices=SLOT_CHOICES)
    award_date = forms.DateField(label='Achievement date', widget=forms.DateInput(attrs={'type': 'date'}))
    shared_note = forms.CharField(label='A message for the athlete and their parents', max_length=500,
                                 required=False, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Example: You kept working on straight legs and showed a big improvement!'}))
    confirm = forms.BooleanField(label='I have checked the achievement and approve sharing this stamp.')
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)
    definition_version = forms.IntegerField(min_value=0, required=False, widget=forms.HiddenInput, initial=0)

    def __init__(self, *args, catalog=None, **kwargs):
        super().__init__(*args, **kwargs)
        if catalog is not None:
            from .passport_badge_services import badge_choices
            self.fields['slot'].choices = badge_choices(catalog)

    def clean_definition_version(self):
        return self.cleaned_data.get('definition_version') or 0

    def clean_award_date(self):
        value = self.cleaned_data['award_date']
        if value > timezone.localdate() or value.year < 2000:
            raise forms.ValidationError('Choose an achievement date from 2000 through today.')
        return value
