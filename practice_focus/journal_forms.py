from django import forms
from django.utils import timezone
from .journal_models import AthleteJournalEntry


class JournalEntryForm(forms.ModelForm):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)

    class Meta:
        model = AthleteJournalEntry
        fields = ['entry_date', 'mood', 'win', 'challenge', 'next_focus',
                  'share_with_coaches', 'share_with_parents']
        labels = {'entry_date': 'Practice date', 'mood': 'How did practice feel?',
                  'win': 'My win today', 'challenge': 'Something I found challenging',
                  'next_focus': 'What I want to work on next',
                  'share_with_coaches': 'Share this entry with my coaches',
                  'share_with_parents': 'Share this entry with my approved linked parents'}
        widgets = {'entry_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
                   'mood': forms.RadioSelect,
                   'win': forms.Textarea(attrs={'rows': 3, 'placeholder': 'A small win counts, too.'}),
                   'challenge': forms.Textarea(attrs={'rows': 3, 'placeholder': 'What felt tricky?'}),
                   'next_focus': forms.Textarea(attrs={'rows': 3, 'placeholder': 'One thing I want to try next time.'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entry_date'].widget.attrs['max'] = timezone.localdate().isoformat()
        self.fields['mood'].choices = AthleteJournalEntry.MOODS
        for name in ('win', 'challenge', 'next_focus'):
            self.fields[name].widget.attrs.update({'maxlength': 1500, 'class': 'aj-input'})
        if self.instance.pk:
            self.fields['entry_date'].disabled = True
            self.fields['version'].initial = self.instance.version


class JournalHistoryForm(forms.Form):
    athlete = forms.IntegerField(required=False, min_value=1)
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('The From date must be on or before the To date.')
        return data
