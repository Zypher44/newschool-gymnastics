from django import forms


class FeedbackForm(forms.Form):
    private_notes = forms.CharField(required=False, max_length=3000, label='Private notes — coaches only', widget=forms.Textarea(attrs={'rows': 3}))
    shared_feedback = forms.CharField(required=False, max_length=3000, label='Shared feedback — athlete and parents can see this', widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        values = super().clean()
        if not values.get('private_notes') and not values.get('shared_feedback'):
            raise forms.ValidationError('Add a private note or shared feedback.')
        return values


class MilestoneForm(forms.Form):
    title = forms.CharField(max_length=150, label='Coach-approved milestone', widget=forms.TextInput(attrs={'placeholder': 'For example: Back handspring achieved'}))


class WeeklyDraftForm(forms.Form):
    week_start = forms.DateField(label='Week beginning', widget=forms.DateInput(attrs={'type': 'date'}))
    coach_feedback = forms.CharField(required=False, max_length=3000, label='Weekly feedback visible to athlete and parents', widget=forms.Textarea(attrs={'rows': 3}))

    def clean_week_start(self):
        from django.utils import timezone
        value = self.cleaned_data['week_start']
        if value.weekday() != 0: raise forms.ValidationError('Choose a Monday so each report covers Monday through Sunday.')
        if value > timezone.localdate(): raise forms.ValidationError('Choose this week or an earlier week.')
        return value
