from django import forms

from coaches.models import CoachAthleteAssignment

from .models import (
    TestingExercise,
    TestingSession,
)


class TestingSessionForm(forms.ModelForm):
    class Meta:
        model = TestingSession

        fields = [
            'title',
            'testing_date',
            'exercises',
            'athletes',
            'notes',
            'allow_athlete_entry',
            'show_rankings_to_athletes',
            'show_rankings_to_parents',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Weekly Physical Testing',
            }),

            'testing_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),

            'exercises': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),

            'athletes': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),

            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional notes for coaches, athletes, or parents.',
            }),

            'allow_athlete_entry': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),

            'show_rankings_to_athletes': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),

            'show_rankings_to_parents': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['exercises'].queryset = TestingExercise.objects.filter(
            active=True
        ).order_by(
            'display_order',
            'name'
        )

        if user is None:
            self.fields['athletes'].queryset = (
                self.fields['athletes'].queryset.none()
            )
            return

        if user.role == 'head_coach':
            athlete_ids = CoachAthleteAssignment.objects.values_list(
                'athlete_id',
                flat=True
            )
        else:
            athlete_ids = CoachAthleteAssignment.objects.filter(
                coach=user
            ).values_list(
                'athlete_id',
                flat=True
            )

        self.fields['athletes'].queryset = (
            self.fields['athletes']
            .queryset
            .filter(id__in=athlete_ids)
            .order_by('first_name', 'last_name', 'username')
            .distinct()
        )

    def clean_exercises(self):
        exercises = self.cleaned_data.get('exercises')

        if not exercises:
            raise forms.ValidationError(
                'Select at least one testing exercise.'
            )

        return exercises

    def clean_athletes(self):
        athletes = self.cleaned_data.get('athletes')

        if not athletes:
            raise forms.ValidationError(
                'Select at least one athlete.'
            )

        return athletes


class TestingExerciseForm(forms.ModelForm):
    class Meta:
        model = TestingExercise

        fields = [
            'name',
            'description',
            'unit',
            'higher_is_better',
            'guidelines',
            'display_order',
            'active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Rope Climb',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of the exercise.',
            }),

            'unit': forms.Select(attrs={
                'class': 'form-select',
            }),

            'higher_is_better': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),

            'guidelines': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': (
                    'Example:\n'
                    '5 pulls = 3 points\n'
                    'White line = 5 points\n'
                    'Under 5 seconds = 10 points'
                ),
            }),

            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),

            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }