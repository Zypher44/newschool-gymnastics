from django import forms
from .models import DailySurvey


class DailySurveyForm(forms.ModelForm):
    class Meta:
        model = DailySurvey
        fields = [
            'survey_date',
            'energy',
            'soreness',
            'stress',
            'sleep_hours',
            'ate_well',
            'hydrated',
            'soreness_area',
            'notes',
        ]
        widgets = {
            'survey_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }