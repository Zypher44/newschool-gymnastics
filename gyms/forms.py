from django import forms
from django.contrib.auth import get_user_model

from .models import (
    GymMembership,
    TrainingGroup,
    TrainingGroupCoach,
)


User = get_user_model()


class TrainingGroupForm(forms.ModelForm):

    class Meta:
        model = TrainingGroup

        fields = [
            'name',
            'level',
            'description',
        ]

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: Level 7 Competitive',
                }
            ),

            'level': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: Level 7',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Optional group description...',
                }
            ),
        }


class ManageGroupCoachesForm(forms.Form):

    head_coach = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label='No head coach selected',
        widget=forms.Select(
            attrs={
                'class': 'form-select'
            }
        )
    )

    coaches = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, gym=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not gym:
            return

        head_coach_ids = (
            GymMembership.objects
            .filter(
                gym=gym,
                role='head_coach',
                is_active=True
            )
            .values_list('user_id', flat=True)
        )

        coach_ids = (
            GymMembership.objects
            .filter(
                gym=gym,
                role__in=['head_coach', 'coach'],
                is_active=True
            )
            .values_list('user_id', flat=True)
        )

        self.fields['head_coach'].queryset = (
            User.objects
            .filter(id__in=head_coach_ids)
            .order_by(
                'first_name',
                'last_name',
                'username'
            )
        )

        self.fields['coaches'].queryset = (
            User.objects
            .filter(id__in=coach_ids)
            .order_by(
                'first_name',
                'last_name',
                'username'
            )
        )

        if group and not self.is_bound:

            current_head_coach = (
                TrainingGroupCoach.objects
                .filter(
                    group=group,
                    role='head_coach'
                )
                .select_related('coach')
                .first()
            )

            current_coaches = (
                TrainingGroupCoach.objects
                .filter(
                    group=group,
                    role__in=['coach', 'assistant']
                )
                .values_list('coach_id', flat=True)
            )

            if current_head_coach:
                self.initial['head_coach'] = current_head_coach.coach

            self.initial['coaches'] = list(current_coaches)


class ManageGroupAthletesForm(forms.Form):

    athletes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, gym=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not gym:
            return

        athlete_ids = (
            GymMembership.objects
            .filter(
                gym=gym,
                role='athlete',
                is_active=True
            )
            .values_list('user_id', flat=True)
        )

        self.fields['athletes'].queryset = (
            User.objects
            .filter(id__in=athlete_ids)
            .order_by(
                'first_name',
                'last_name',
                'username'
            )
        )

        if group and not self.is_bound:

            current_athletes = (
                group.athlete_assignments
                .filter(is_active=True)
                .values_list('athlete_id', flat=True)
            )

            self.initial['athletes'] = list(current_athletes)

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class CreateGymPersonForm(forms.Form):

    ROLE_CHOICES = [
        ('head_coach', 'Head Coach'),
        ('coach', 'Coach'),
        ('athlete', 'Athlete'),
        ('parent', 'Parent / Guardian'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
                'id': 'id_role',
            }
        )
    )

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }
        )
    )

    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Email address',
            }
        )
    )

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Username',
            }
        )
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Temporary password',
            }
        )
    )

    # Coach-specific fields
    title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Example: Optional Team Coach',
            }
        )
    )

    phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Phone number',
            }
        )
    )

    # Athlete-specific fields
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
            }
        )
    )

    level = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Example: Level 7',
            }
        )
    )

    emergency_contact_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )

    emergency_contact_phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )

    emergency_contact_relationship = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Parent, guardian, etc.',
            }
        )
    )

    medical_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
            }
        )
    )

    def clean_username(self):

        username = self.cleaned_data['username']

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                'A user with this username already exists.'
            )

        return username


class EditGymPersonForm(forms.Form):

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
            }
        )
    )

    level = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    emergency_contact_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    emergency_contact_phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    emergency_contact_relationship = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    medical_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
            }
        )
    )


from django import forms

from gyms.models import GymMembership


class LinkParentGuardianForm(forms.Form):
    parent = forms.ModelChoiceField(
        queryset=GymMembership.objects.none(),
        label='Parent / Guardian',
        empty_label='Select a parent or guardian',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
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

    def __init__(self, *args, gym=None, **kwargs):
        super().__init__(*args, **kwargs)

        if gym:
            self.fields['parent'].queryset = (
                GymMembership.objects
                .filter(
                    gym=gym,
                    role='parent',
                    is_active=True,
                )
                .select_related('user')
                .order_by(
                    'user__first_name',
                    'user__last_name',
                    'user__username',
                )
            )

    def clean_parent(self):
        membership = self.cleaned_data['parent']

        if membership.role != 'parent':
            raise forms.ValidationError(
                'Selected person must be a parent or guardian.'
            )

        return membership