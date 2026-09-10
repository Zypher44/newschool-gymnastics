from django import forms

from .models import (
    AthleteRoutine,
    AthleteRoutineElement,
)


class AthleteRoutineForm(forms.ModelForm):

    class Meta:
        model = AthleteRoutine

        fields = [
            'name',
            'pathway_level',
            'event',
            'is_current',
            'notes',
        ]

        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),

            'pathway_level': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'event': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'is_current': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),

            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                }
            ),
        }


class AthleteRoutineElementForm(forms.ModelForm):

    class Meta:
        model = AthleteRoutineElement

        fields = [
            'skill_name',
            'difficulty',
            'vault_value',
            'element_type',
            'order',
            'is_dismount',
            'notes',
        ]

        widgets = {
            'skill_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: Pak Salto',
                }
            ),

            'difficulty': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'element_type': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'order': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                }
            ),

            'is_dismount': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),

            'notes': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),

            'vault_value': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': 'Example: 4.50',
                }
            ),
        }