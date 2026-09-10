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