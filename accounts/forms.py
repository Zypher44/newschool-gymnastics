from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm


User = get_user_model()


class AccountProfileForm(forms.ModelForm):
    current_password = forms.CharField(
        required=False,
        label='Current password',
        help_text='Required only when changing your email address.',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password',
        }),
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'autocomplete': 'email',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'tel',
                'placeholder': 'Example: 519-555-0123',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user or self.instance
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        duplicate = User.objects.filter(email__iexact=email)

        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )

        return email

    def clean_phone(self):
        return self.cleaned_data.get('phone', '').strip()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')

        if (
            email
            and self.instance.pk
            and email.lower() != (self.instance.email or '').lower()
        ):
            password = cleaned_data.get('current_password')

            if not password:
                self.add_error(
                    'current_password',
                    'Enter your current password to change your email.',
                )
            elif not self.user.check_password(password):
                self.add_error(
                    'current_password',
                    'Your current password is incorrect.',
                )

        return cleaned_data


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
            })

        self.fields['old_password'].widget.attrs.update({
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'autocomplete': 'new-password',
        })


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
