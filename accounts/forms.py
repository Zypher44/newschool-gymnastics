from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


User = get_user_model()


class PublicSignUpForm(UserCreationForm):
    ROLE_CHOICES = [
        ('athlete', 'Athlete'),
        ('parent', 'Parent or Guardian'),
    ]

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'First name',
                'autocomplete': 'given-name',
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
                'autocomplete': 'family-name',
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Email address',
                'autocomplete': 'email',
            }
        ),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect(),
    )

    class Meta(UserCreationForm.Meta):
        model = User

        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'role',
            'password1',
            'password2',
        ]

        widgets = {
            'username': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Choose a username',
                    'autocomplete': 'username',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        })

        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })

        self.fields['username'].help_text = (
            'Use letters, numbers, and common symbols only.'
        )

        self.fields['password1'].help_text = (
            'Use at least 8 characters and avoid common passwords.'
        )

        self.fields['password2'].help_text = (
            'Enter the same password again for verification.'
        )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists.'
            )

        return email

    def clean_role(self):
        role = self.cleaned_data['role']

        allowed_roles = {
            'athlete',
            'parent',
        }

        if role not in allowed_roles:
            raise forms.ValidationError(
                'This account type cannot be created publicly.'
            )

        return role

    def save(self, commit=True):
        user = super().save(commit=False)

        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email'].strip().lower()
        user.role = self.cleaned_data['role']

        if commit:
            user.save()

        return user