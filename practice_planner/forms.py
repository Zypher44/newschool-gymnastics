from django import forms
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from performance_testing.models import TestingSession

from .models import (
    PracticeAthleteAssignment,
    PracticePlan,
    PracticeRotation,
    PracticeStation,
    PracticeTemplate,
    TrainingGroup,

)


User = get_user_model()


class BootstrapFormMixin:
    """
    Adds Bootstrap classes to standard Django form fields.
    """

    def apply_bootstrap_classes(self):
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                continue

            if isinstance(
                widget,
                (
                    forms.Select,
                    forms.SelectMultiple,
                ),
            ):
                current_class = widget.attrs.get(
                    'class',
                    '',
                )

                widget.attrs['class'] = (
                    f'{current_class} form-select'
                ).strip()

            else:
                current_class = widget.attrs.get(
                    'class',
                    '',
                )

                widget.attrs['class'] = (
                    f'{current_class} form-control'
                ).strip()


class TrainingGroupForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = TrainingGroup

        fields = [
            'name',
            'description',
            'coaches',
            'athletes',
            'is_active',
        ]

        widgets = {
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': (
                        'Optional description of this '
                        'training group.'
                    ),
                },
            ),
            'coaches': forms.CheckboxSelectMultiple(),
            'athletes': forms.CheckboxSelectMultiple(),
            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
        }

    def __init__(
        self,
        *args,
        user=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields['coaches'].queryset = (
            User.objects.filter(
                role__in=[
                    'coach',
                    'head_coach',
                ],
                is_active=True,
            )
            .order_by(
                'first_name',
                'last_name',
                'username',
            )
        )

        self.fields['athletes'].queryset = (
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

        self.apply_bootstrap_classes()

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        duplicate_groups = TrainingGroup.objects.filter(
            name__iexact=name,
        )

        if self.instance.pk:
            duplicate_groups = duplicate_groups.exclude(
                pk=self.instance.pk,
            )

        if duplicate_groups.exists():
            raise forms.ValidationError(
                'A training group with this name already exists.'
            )

        return name


class PracticePlanForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = PracticePlan

        fields = [
            'title',
            'practice_date',
            'start_time',
            'end_time',
            'training_group',
            'lead_coach',
            'assistant_coaches',
            'status',
            'planned_intensity',
            'primary_focus',
            'coach_objectives',
            'general_notes',
        ]

        widgets = {
            'title': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: WAG A Thursday Practice'
                    ),
                },
            ),
            'practice_date': forms.DateInput(
                attrs={
                    'type': 'date',
                },
            ),
            'start_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                },
            ),
            'end_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                },
            ),
            'assistant_coaches': (
                forms.CheckboxSelectMultiple()
            ),
            'primary_focus': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Bar releases and '
                        'beam connections'
                    ),
                },
            ),
            'coach_objectives': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': (
                        'What should the athletes accomplish '
                        'during this practice?'
                    ),
                },
            ),
            'general_notes': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': (
                        'Optional general practice notes.'
                    ),
                },
            ),
        }

    def __init__(
        self,
        *args,
        user=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        coach_queryset = (
            User.objects.filter(
                role__in=[
                    'coach',
                    'head_coach',
                ],
                is_active=True,
            )
            .order_by(
                'first_name',
                'last_name',
                'username',
            )
        )

        self.fields['lead_coach'].queryset = (
            coach_queryset
        )

        self.fields['assistant_coaches'].queryset = (
            coach_queryset
        )

        if user and not self.instance.pk:
            if user.role in [
                'coach',
                'head_coach',
            ]:
                self.fields['lead_coach'].initial = user

        if user and user.role == 'coach':
            self.fields['training_group'].queryset = (
                TrainingGroup.objects.filter(
                    coaches=user,
                    is_active=True,
                )
                .distinct()
                .order_by('name')
            )

        else:
            self.fields['training_group'].queryset = (
                TrainingGroup.objects.filter(
                    is_active=True,
                )
                .order_by('name')
            )

        self.apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get(
            'start_time'
        )

        end_time = cleaned_data.get(
            'end_time'
        )

        if (
            start_time
            and end_time
            and end_time <= start_time
        ):
            self.add_error(
                'end_time',
                (
                    'The practice end time must be after '
                    'the start time.'
                ),
            )

        return cleaned_data


class PracticeRotationForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = PracticeRotation

        fields = [
            'title',
            'event',
            'order',
            'start_time',
            'duration_minutes',
            'location',
            'assigned_coach',
            'objective',
            'coach_notes',
            'testing_session',
        ]

        widgets = {
            'title': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Bars Rotation'
                    ),
                },
            ),
            'start_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                },
            ),
            'duration_minutes': forms.NumberInput(
                attrs={
                    'min': 1,
                },
            ),
            'location': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Main gym, Beam 2'
                    ),
                },
            ),
            'objective': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Primary objective for this rotation'
                    ),
                },
            ),
            'coach_notes': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': (
                        'Optional notes for the assigned coach.'
                    ),
                },
            ),
        }

    def __init__(
        self,
        *args,
        practice_plan=None,
        user=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.practice_plan = practice_plan

        self.fields['assigned_coach'].queryset = (
            User.objects.filter(
                role__in=[
                    'coach',
                    'head_coach',
                ],
                is_active=True,
            )
            .order_by(
                'first_name',
                'last_name',
                'username',
            )
        )

        testing_sessions = TestingSession.objects.all()

        if practice_plan:
            testing_sessions = (
                testing_sessions.filter(
                    testing_date=(
                        practice_plan.practice_date
                    ),
                )
                .filter(
                    models.Q(
                        training_group=(
                            practice_plan.training_group
                        ),
                    )
                    | models.Q(
                        training_group__isnull=True,
                    )
                )
                .filter(
                    models.Q(
                        practice_plan=practice_plan,
                    )
                    | models.Q(
                        practice_plan__isnull=True,
                    )
                )
            )

        self.fields['testing_session'].queryset = (
            testing_sessions
            .select_related(
                'training_group',
                'practice_plan',
            )
            .order_by(
                '-testing_date',
                'title',
            )
        )

        self.fields['testing_session'].required = False

        self.fields['testing_session'].empty_label = (
            'Select an existing testing session'
        )

        self.apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()

        event = cleaned_data.get(
            'event'
        )

        testing_session = cleaned_data.get(
            'testing_session'
        )

        if (
            event == PracticeRotation.EVENT_TESTING
            and not testing_session
        ):
            self.add_error(
                'testing_session',
                (
                    'Choose a Performance Testing session '
                    'for this testing rotation.'
                ),
            )

        if (
            event != PracticeRotation.EVENT_TESTING
            and testing_session
        ):
            self.add_error(
                'testing_session',
                (
                    'Testing sessions can only be selected '
                    'for a testing rotation.'
                ),
            )

        if (
            testing_session
            and self.practice_plan
        ):
            if (
                testing_session.testing_date
                != self.practice_plan.practice_date
            ):
                self.add_error(
                    'testing_session',
                    (
                        'The testing session date must match '
                        'the practice date.'
                    ),
                )

            if (
                testing_session.training_group_id
                and testing_session.training_group_id
                != self.practice_plan.training_group_id
            ):
                self.add_error(
                    'testing_session',
                    (
                        'The testing session group must match '
                        'the practice training group.'
                    ),
                )

            if (
                testing_session.practice_plan_id
                and testing_session.practice_plan_id
                != self.practice_plan.id
            ):
                self.add_error(
                    'testing_session',
                    (
                        'This testing session is already '
                        'connected to another practice.'
                    ),
                )

        return cleaned_data

    def save(
        self,
        commit=True,
    ):
        rotation = super().save(
            commit=False,
        )

        if self.practice_plan:
            rotation.practice_plan = (
                self.practice_plan
            )

        rotation.is_testing_rotation = (
            rotation.event
            == PracticeRotation.EVENT_TESTING
        )

        if commit:
            rotation.save()

            if rotation.testing_session_id:
                testing_session = (
                    rotation.testing_session
                )

                changed_fields = []

                if (
                    testing_session.practice_plan_id
                    is None
                ):
                    testing_session.practice_plan = (
                        rotation.practice_plan
                    )

                    changed_fields.append(
                        'practice_plan'
                    )

                if (
                    testing_session.training_group_id
                    is None
                ):
                    testing_session.training_group = (
                        rotation.practice_plan.training_group
                    )

                    changed_fields.append(
                        'training_group'
                    )

                if changed_fields:
                    testing_session.save(
                        update_fields=changed_fields,
                    )

                testing_session.copy_group_athletes()

        return rotation


class PracticeStationForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = PracticeStation

        fields = [
            'title',
            'station_type',
            'order',
            'duration_minutes',
            'sets',
            'repetitions',
            'target_attempts',
            'instructions',
            'coaching_cues',
            'equipment',
            'success_criteria',
            'reference_video_url',
            'is_optional',
        ]

        widgets = {
            'title': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Cast handstand drill'
                    ),
                },
            ),
            'duration_minutes': forms.NumberInput(
                attrs={
                    'min': 1,
                },
            ),
            'sets': forms.NumberInput(
                attrs={
                    'min': 1,
                },
            ),
            'repetitions': forms.NumberInput(
                attrs={
                    'min': 1,
                },
            ),
            'target_attempts': forms.NumberInput(
                attrs={
                    'min': 1,
                },
            ),
            'instructions': forms.Textarea(
                attrs={
                    'rows': 3,
                },
            ),
            'coaching_cues': forms.Textarea(
                attrs={
                    'rows': 3,
                },
            ),
            'equipment': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Panel mat, low bar'
                    ),
                },
            ),
            'success_criteria': forms.Textarea(
                attrs={
                    'rows': 3,
                },
            ),
            'reference_video_url': forms.URLInput(
                attrs={
                    'placeholder': (
                        'https://example.com/video'
                    ),
                },
            ),
            'is_optional': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
        }

    def __init__(
        self,
        *args,
        rotation=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.rotation = rotation

        self.apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()

        if (
            self.rotation
            and self.rotation.is_testing_rotation
        ):
            raise forms.ValidationError(
                (
                    'Testing exercises are managed through '
                    'the linked Performance Testing session. '
                    'Do not add practice stations to a '
                    'testing rotation.'
                )
            )

        return cleaned_data

    def save(
        self,
        commit=True,
    ):
        station = super().save(
            commit=False,
        )

        if self.rotation:
            station.rotation = self.rotation

        if commit:
            station.save()

        return station


class PracticeAthleteAssignmentForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = PracticeAthleteAssignment

        fields = [
            'athlete',
            'workload',
            'is_expected',
            'restrictions',
            'individual_focus',
            'coach_notes',
        ]

        widgets = {
            'is_expected': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
            'restrictions': forms.Textarea(
                attrs={
                    'rows': 2,
                },
            ),
            'individual_focus': forms.Textarea(
                attrs={
                    'rows': 2,
                },
            ),
            'coach_notes': forms.Textarea(
                attrs={
                    'rows': 2,
                },
            ),
        }

    def __init__(
        self,
        *args,
        practice_plan=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.practice_plan = practice_plan

        athlete_queryset = User.objects.filter(
            role='athlete',
            is_active=True,
        )

        if practice_plan:
            athlete_queryset = (
                athlete_queryset.filter(
                    practice_groups=(
                        practice_plan.training_group
                    ),
                )
            )

        self.fields['athlete'].queryset = (
            athlete_queryset.order_by(
                'first_name',
                'last_name',
                'username',
            )
        )

        self.apply_bootstrap_classes()

    def save(
        self,
        commit=True,
    ):
        assignment = super().save(
            commit=False,
        )

        if self.practice_plan:
            assignment.practice_plan = (
                self.practice_plan
            )

        if commit:
            assignment.save()

        return assignment

class SavePracticeTemplateForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = PracticeTemplate

        fields = [
            'name',
            'description',
            'category',
            'level',
            'season_phase',
            'is_shared',
        ]

        widgets = {
            'name': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: HP Monday Practice'
                    ),
                },
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': (
                        'Describe when and how this template '
                        'should be used.'
                    ),
                },
            ),
            'level': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: HP Novice'
                    ),
                },
            ),
            'season_phase': forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: Competition Season'
                    ),
                },
            ),
            'is_shared': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
        }

    def __init__(
        self,
        *args,
        user=None,
        practice_plan=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.user = user
        self.practice_plan = practice_plan

        if practice_plan and not self.is_bound:
            self.fields['name'].initial = (
                practice_plan.title
            )

            self.fields['description'].initial = (
                practice_plan.general_notes
            )

            self.fields['level'].initial = (
                practice_plan.training_group.name
            )

        self.apply_bootstrap_classes()

    def clean_name(self):
        name = self.cleaned_data[
            'name'
        ].strip()

        if self.user:
            duplicate = (
                PracticeTemplate.objects
                .filter(
                    created_by=self.user,
                    name__iexact=name,
                )
            )

            if duplicate.exists():
                raise forms.ValidationError(
                    (
                        'You already have a practice template '
                        'with this name.'
                    )
                )

        return name

class CreatePracticeFromTemplateForm(
        BootstrapFormMixin,
        forms.Form,
    ):
        title = forms.CharField(
            max_length=180,
            widget=forms.TextInput(
                attrs={
                    'placeholder': (
                        'Example: HP Monday Practice'
                    ),
                },
            ),
        )

        practice_date = forms.DateField(
            widget=forms.DateInput(
                attrs={
                    'type': 'date',
                },
            ),
        )

        start_time = forms.TimeField(
            widget=forms.TimeInput(
                attrs={
                    'type': 'time',
                },
            ),
        )

        end_time = forms.TimeField(
            widget=forms.TimeInput(
                attrs={
                    'type': 'time',
                },
            ),
        )

        training_group = forms.ModelChoiceField(
            queryset=TrainingGroup.objects.none(),
        )

        lead_coach = forms.ModelChoiceField(
            queryset=User.objects.none(),
        )

        assistant_coaches = forms.ModelMultipleChoiceField(
            queryset=User.objects.none(),
            required=False,
            widget=forms.CheckboxSelectMultiple(),
        )

        status = forms.ChoiceField(
            choices=PracticePlan.STATUS_CHOICES,
            initial=PracticePlan.STATUS_DRAFT,
        )

        planned_intensity = forms.ChoiceField(
            choices=PracticePlan.INTENSITY_CHOICES,
        )

        primary_focus = forms.CharField(
            max_length=200,
            required=False,
            widget=forms.TextInput(),
        )

        coach_objectives = forms.CharField(
            required=False,
            widget=forms.Textarea(
                attrs={
                    'rows': 3,
                },
            ),
        )

        general_notes = forms.CharField(
            required=False,
            widget=forms.Textarea(
                attrs={
                    'rows': 3,
                },
            ),
        )

        scale_rotation_durations = forms.BooleanField(
            required=False,
            initial=True,
            label=(
                'Automatically scale rotation durations '
                'to fit the new practice'
            ),
            widget=forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
        )

        include_testing_rotations = forms.BooleanField(
            required=False,
            initial=True,
            label='Include testing rotations',
            widget=forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                },
            ),
        )

        include_optional_rotations = forms.BooleanField(
            required=False,
            initial=True,
            label='Include optional rotations',
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
                practice_template=None,
                **kwargs,
        ):
            super().__init__(
                *args,
                **kwargs,
            )

            self.user = user
            self.practice_template = practice_template

            coaches = (
                User.objects.filter(
                    role__in=[
                        'coach',
                        'head_coach',
                    ],
                    is_active=True,
                )
                .order_by(
                    'first_name',
                    'last_name',
                    'username',
                )
            )

            self.fields[
                'lead_coach'
            ].queryset = coaches

            self.fields[
                'assistant_coaches'
            ].queryset = coaches

            if user and user.role == 'coach':
                self.fields[
                    'training_group'
                ].queryset = (
                    TrainingGroup.objects.filter(
                        coaches=user,
                        is_active=True,
                    )
                    .distinct()
                    .order_by(
                        'name',
                    )
                )

            else:
                self.fields[
                    'training_group'
                ].queryset = (
                    TrainingGroup.objects.filter(
                        is_active=True,
                    )
                    .order_by(
                        'name',
                    )
                )

            if practice_template and not self.is_bound:
                self.fields['title'].initial = (
                    practice_template.name
                )

                self.fields[
                    'planned_intensity'
                ].initial = (
                    practice_template.planned_intensity
                )

                self.fields[
                    'primary_focus'
                ].initial = (
                    practice_template.primary_focus
                )

                self.fields[
                    'coach_objectives'
                ].initial = (
                    practice_template.coach_objectives
                )

                self.fields[
                    'general_notes'
                ].initial = (
                    practice_template.general_notes
                )

                has_testing = (
                    practice_template.rotations.filter(
                        include_testing=True,
                    ).exists()
                )

                self.fields[
                    'include_testing_rotations'
                ].initial = has_testing

                has_optional = (
                    practice_template.rotations.filter(
                        is_optional=True,
                    ).exists()
                )

                self.fields[
                    'include_optional_rotations'
                ].initial = has_optional

            if (
                    user
                    and not self.is_bound
                    and user.role in [
                'coach',
                'head_coach',
            ]
            ):
                self.fields[
                    'lead_coach'
                ].initial = user

            self.apply_bootstrap_classes()

        def clean(self):
            cleaned_data = super().clean()

            practice_date = cleaned_data.get(
                'practice_date'
            )

            start_time = cleaned_data.get(
                'start_time'
            )

            end_time = cleaned_data.get(
                'end_time'
            )

            if (
                    practice_date
                    and start_time
                    and end_time
            ):
                start_datetime = (
                    timezone.datetime.combine(
                        practice_date,
                        start_time,
                    )
                )

                end_datetime = (
                    timezone.datetime.combine(
                        practice_date,
                        end_time,
                    )
                )

                if end_datetime <= start_datetime:
                    self.add_error(
                        'end_time',
                        (
                            'The practice end time must be '
                            'after the start time.'
                        ),
                    )

                    return cleaned_data

                duration_minutes = int(
                    (
                            end_datetime
                            - start_datetime
                    ).total_seconds()
                    / 60
                )

                cleaned_data[
                    'target_duration_minutes'
                ] = duration_minutes

                if self.practice_template:
                    rotations = (
                        self.practice_template.rotations
                        .all()
                    )

                    if not cleaned_data.get(
                            'include_testing_rotations'
                    ):
                        rotations = rotations.exclude(
                            include_testing=True,
                        )

                    if not cleaned_data.get(
                            'include_optional_rotations'
                    ):
                        rotations = rotations.exclude(
                            is_optional=True,
                        )

                    rotation_count = rotations.count()

                    if rotation_count == 0:
                        raise forms.ValidationError(
                            (
                                'The selected options remove every '
                                'rotation from this template.'
                            )
                        )

                    if (
                            cleaned_data.get(
                                'scale_rotation_durations'
                            )
                            and duration_minutes < rotation_count
                    ):
                        raise forms.ValidationError(
                            (
                                'The practice is too short to assign '
                                'at least one minute to every rotation.'
                            )
                        )

            return cleaned_data

def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get(
            'start_time'
        )

        end_time = cleaned_data.get(
            'end_time'
        )

        if (
            start_time
            and end_time
            and end_time <= start_time
        ):
            self.add_error(
                'end_time',
                (
                    'The practice end time must be after '
                    'the start time.'
                ),
            )

        return cleaned_data