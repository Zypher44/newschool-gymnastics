from django import forms
from .passport_catalog import BADGES

ICON_CHOICES = [(value, value) for value in dict.fromkeys([icon for _, icon, _, _ in BADGES] +
                ['🏅', '🥇', '💪', '🔥', '🎉', '💎', '🦋', '🦄', '🦁', '📚', '❤️', '⭐'])]


class BadgeEditorForm(forms.Form):
    title = forms.CharField(label='Badge name', max_length=80)
    icon = forms.ChoiceField(label='Badge emoji', choices=ICON_CHOICES, initial='🏅')
    description = forms.CharField(label='How to earn this badge', max_length=400,
                                  widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Example: Help a teammate learn a new warm-up.'}))
    is_active = forms.BooleanField(label='Available for new awards', required=False, initial=True)
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'version':
                field.widget.attrs['class'] = 'form-check-input' if name == 'is_active' else 'form-select' if name == 'icon' else 'form-control'
