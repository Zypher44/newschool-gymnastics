from uuid import UUID

from django import forms
from django.core import signing

from .models import PublicEnquiry


TOKEN_SALT = 'accounts.public-enquiry'


class PublicEnquiryForm(forms.ModelForm):
    submission_token = forms.CharField(widget=forms.HiddenInput)
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'tabindex': '-1', 'autocomplete': 'off',
    }))
    consent_to_reply = forms.BooleanField(
        label='NewSchool Gymnastics may use these details to respond to my enquiry.',
    )

    class Meta:
        model = PublicEnquiry
        fields = ['name', 'email', 'gym_name', 'kind', 'message', 'consent_to_reply']
        labels = {
            'name': 'Your name', 'email': 'Email address', 'gym_name': 'Gym name (optional)',
            'kind': "I'd like to discuss", 'message': 'What would you like help with? (optional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'gym_name': forms.TextInput(attrs={'autocomplete': 'organization'}),
            'message': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = (
                'form-check-input' if isinstance(field.widget, forms.CheckboxInput)
                else 'form-select' if isinstance(field.widget, forms.Select)
                else 'form-control'
            )

    def clean_submission_token(self):
        try:
            return UUID(signing.loads(
                self.cleaned_data['submission_token'], salt=TOKEN_SALT, max_age=7200,
            ))
        except (signing.BadSignature, ValueError, TypeError):
            raise forms.ValidationError('This form expired. Refresh the page and try again.')

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Please leave this field empty.')
        return ''
