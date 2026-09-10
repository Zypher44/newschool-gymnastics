from django import forms

from .models import (
    AthletePathway,
)


class AthletePathwayForm(
    forms.ModelForm
):
    class Meta:
        model = AthletePathway

        fields = [
            'current_level',
            'target_level',
            'status',
            'target_date',
            'head_coach_notes',
        ]

        widgets = {
            'current_level': (
                forms.Select(
                    attrs={
                        'class': 'form-select',
                    }
                )
            ),

            'target_level': (
                forms.Select(
                    attrs={
                        'class': 'form-select',
                    }
                )
            ),

            'status': (
                forms.Select(
                    attrs={
                        'class': 'form-select',
                    }
                )
            ),

            'target_date': (
                forms.DateInput(
                    attrs={
                        'class': 'form-control',
                        'type': 'date',
                    }
                )
            ),

            'head_coach_notes': (
                forms.Textarea(
                    attrs={
                        'class': 'form-control',
                        'rows': 4,
                        'placeholder': (
                            'Head coach notes about '
                            'this athlete’s pathway...'
                        ),
                    }
                )
            ),
        }