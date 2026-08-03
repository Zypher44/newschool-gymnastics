from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model

from practice_planner.models import (
    PracticePlan,
    TrainingGroup,
)

from .models import Video


User = get_user_model()


class MultipleVideoInput(
    forms.ClearableFileInput,
):
    allow_multiple_selected = True


class MultipleVideoField(
    forms.FileField,
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        kwargs.setdefault(
            'widget',
            MultipleVideoInput(
                attrs={
                    'accept': 'video/*',
                    'multiple': True,
                    'class': 'form-control',
                },
            ),
        )

        super().__init__(
            *args,
            **kwargs,
        )

    def clean(
        self,
        data,
        initial=None,
    ):
        single_file_clean = super().clean

        if isinstance(
            data,
            (
                list,
                tuple,
            ),
        ):
            result = [
                single_file_clean(
                    uploaded_file,
                    initial,
                )
                for uploaded_file in data
            ]

        else:
            result = [
                single_file_clean(
                    data,
                    initial,
                )
            ]

        return result


class VideoUploadForm(forms.Form):
    videos = MultipleVideoField(
        label='Select Videos',
        help_text=(
            'Select one or more videos from your phone or computer.'
        ),
    )

    title_prefix = forms.CharField(
        max_length=120,
        required=False,
        label='Title Prefix',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': (
                    'Example: Bars Training'
                ),
            },
        ),
        help_text=(
            'Optional. The original filename will be used '
            'when this is left blank.'
        ),
    )

    primary_athlete = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Primary Athlete',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    tagged_athletes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Additional Athletes',
        widget=forms.CheckboxSelectMultiple(),
    )

    training_group = forms.ModelChoiceField(
        queryset=TrainingGroup.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    practice_plan = forms.ModelChoiceField(
        queryset=PracticePlan.objects.none(),
        required=False,
        label='Practice',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    event = forms.ChoiceField(
        choices=Video.EVENT_CHOICES,
        initial=Video.EVENT_OTHER,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    skill_name = forms.CharField(
        max_length=150,
        required=False,
        label='Skill',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': (
                    'Example: Jager, Pak salto, beam series'
                ),
            },
        ),
    )

    video_type = forms.ChoiceField(
        choices=Video.VIDEO_TYPE_CHOICES,
        initial=Video.TYPE_PRACTICE,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    recorded_date = forms.DateField(
        required=False,
        label='Date Recorded',
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
            },
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': (
                    'Add coaching notes that apply to these videos.'
                ),
            },
        ),
    )

    tags = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': (
                    'release, personal best, competition prep'
                ),
            },
        ),
    )

    visibility = forms.ChoiceField(
        choices=Video.VISIBILITY_CHOICES,
        initial=Video.VISIBILITY_COACHES,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            },
        ),
    )

    mark_as_favorite = forms.BooleanField(
        required=False,
        label='Mark uploaded videos as favorites',
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input',
            },
        ),
    )

    request_ai_analysis = forms.BooleanField(
        required=False,
        label='Add videos to the future AI analysis queue',
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input',
            },
        ),
    )

    def __init__(
        self,
        *args,
        user=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.user = user

        athletes = (
            User.objects.filter(
                role='athlete',
                is_active=True,
            )
            .order_by(
                'first_name',
                'last_name',
                'username',
            )
        )

        self.fields[
            'primary_athlete'
        ].queryset = athletes

        self.fields[
            'tagged_athletes'
        ].queryset = athletes

        groups = TrainingGroup.objects.filter(
            is_active=True,
        )

        practices = (
            PracticePlan.objects
            .select_related(
                'training_group',
            )
            .exclude(
                status=PracticePlan.STATUS_CANCELLED,
            )
        )

        if user and user.role == 'coach':
            groups = groups.filter(
                coaches=user,
            ).distinct()

            practices = practices.filter(
                training_group__coaches=user,
            ).distinct()

        self.fields[
            'training_group'
        ].queryset = groups.order_by(
            'name',
        )

        self.fields[
            'practice_plan'
        ].queryset = practices.order_by(
            '-practice_date',
            '-start_time',
        )

    def clean_videos(self):
        videos = self.cleaned_data[
            'videos'
        ]

        allowed_extensions = {
            '.mp4',
            '.mov',
            '.m4v',
            '.webm',
            '.avi',
        }

        maximum_file_size = (
            500
            * 1024
            * 1024
        )

        errors = []

        for uploaded_file in videos:
            extension = Path(
                uploaded_file.name
            ).suffix.lower()

            if extension not in allowed_extensions:
                errors.append(
                    (
                        f'{uploaded_file.name}: '
                        f'unsupported video format.'
                    )
                )

            if uploaded_file.size > maximum_file_size:
                errors.append(
                    (
                        f'{uploaded_file.name}: '
                        f'file exceeds the 500 MB limit.'
                    )
                )

            content_type = getattr(
                uploaded_file,
                'content_type',
                '',
            )

            if (
                content_type
                and not content_type.startswith(
                    'video/'
                )
            ):
                errors.append(
                    (
                        f'{uploaded_file.name}: '
                        f'this does not appear to be a video.'
                    )
                )

        if errors:
            raise forms.ValidationError(
                errors
            )

        return videos

    def clean(self):
        cleaned_data = super().clean()

        practice_plan = cleaned_data.get(
            'practice_plan'
        )

        training_group = cleaned_data.get(
            'training_group'
        )

        primary_athlete = cleaned_data.get(
            'primary_athlete'
        )

        tagged_athletes = cleaned_data.get(
            'tagged_athletes'
        )

        if (
            practice_plan
            and training_group
            and practice_plan.training_group_id
            != training_group.id
        ):
            self.add_error(
                'training_group',
                (
                    'The selected group must match '
                    'the selected practice.'
                ),
            )

        if (
            primary_athlete
            and tagged_athletes
            and primary_athlete in tagged_athletes
        ):
            self.add_error(
                'tagged_athletes',
                (
                    'The primary athlete does not need to '
                    'be selected again as an additional athlete.'
                ),
            )

        return cleaned_data