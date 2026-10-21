from django import forms


class ConnectAthleteForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label='Athlete First Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        label='Athlete Last Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }
        ),
    )

    date_of_birth = forms.DateField(
        label='Athlete Date of Birth',
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
            }
        ),
    )

    relationship = forms.CharField(
        max_length=50,
        label='Relationship',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Example: Mother, Father, Guardian',
            }
        ),
    )

class AthleteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, athlete):
        name = athlete.get_full_name().strip() or athlete.username
        return f'{name} ({athlete.username})'


from django.contrib.auth import get_user_model


class ConnectAthleteDropdownForm(forms.Form):
    athlete = AthleteChoiceField(queryset=get_user_model().objects.none(), label='Choose your child', empty_label='Select an athlete', widget=forms.Select(attrs={'class': 'form-select'}))
    date_of_birth = forms.DateField(label="Child's date of birth", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    relationship = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        from .access import get_parent_gym_ids
        self.fields['athlete'].queryset = get_user_model().objects.filter(role='athlete', is_active=True,
            gym_memberships__gym_id__in=get_parent_gym_ids(user), gym_memberships__is_active=True,
            gym_memberships__role='athlete').distinct().order_by('first_name', 'last_name', 'username')

    def clean(self):
        data = super().clean()
        athlete, dob = data.get('athlete'), data.get('date_of_birth')
        profile = getattr(athlete, 'athlete_profile', None) if athlete else None
        if athlete and dob and (profile is None or profile.date_of_birth != dob):
            raise forms.ValidationError('The athlete and date of birth did not match. Check the details with your gym director.')
        return data
