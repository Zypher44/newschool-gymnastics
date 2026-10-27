from django import forms

from accounts.models import User

from .services import get_allowed_message_recipients


class NewConversationForm(forms.Form):
    observer = forms.ModelChoiceField(queryset=User.objects.none(), required=False,
        empty_label='Choose an approved parent or second coach',
        label='Observer for an athlete conversation',
        help_text='Everyone selected can see the whole new thread. This does not add anyone to earlier conversations.')
    recipient = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label='Choose a recipient'
    )

    subject = forms.CharField(
        max_length=180,
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Optional subject'
            }
        )
    )

    message = forms.CharField(
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                'rows': 5,
                'placeholder': (
                    'Write your message...'
                ),
            }
        )
    )

    def __init__(
        self,
        *args,
        user=None,
        **kwargs
    ):
        super().__init__(
            *args,
            **kwargs
        )

        if user:
            self.user = user
            self.fields[
                'recipient'
            ].queryset = (
                get_allowed_message_recipients(
                    user
                )
            )
            from .safeguarding import active_members, eligible_observers, OBSERVER_ROLES
            from gyms.tenant import single_active_gym_id
            from django.db.models import Q
            from parents_portal.models import ParentAthleteLink
            gym_id = single_active_gym_id(user, [user.role])
            recipient_id = (self.data.get('recipient') if self.is_bound else self.initial.get('recipient'))
            recipient = self.fields['recipient'].queryset.filter(pk=recipient_id).first() if str(recipient_id or '').isdigit() else None
            if recipient:
                self.fields['observer'].queryset = eligible_observers(user, recipient)
            else:
                candidates = active_members(gym_id).filter(role__in=OBSERVER_ROLES + ('parent',)).exclude(pk=user.pk)
                if user.role == 'athlete':
                    parents = ParentAthleteLink.objects.filter(athlete=user, approved=True).values('parent_id')
                    candidates = candidates.filter(Q(role__in=OBSERVER_ROLES) | Q(role='parent', pk__in=parents))
                self.fields['observer'].queryset = candidates.order_by('role', 'first_name', 'username')
            self.fields['observer'].label_from_instance = lambda person: f'{person.get_full_name() or person.username} ({person.get_role_display()})'
            self.fields['recipient'].label_from_instance = lambda person: f'{person.get_full_name() or person.username} ({person.get_role_display()})'

        for field in self.fields.values():
            field.widget.attrs[
                'class'
            ] = 'form-control'

    def clean(self):
        data = super().clean()
        if data.get('recipient'):
            from .safeguarding import supervised_pair
            try:
                supervised_pair(self.user, data['recipient'], data.get('observer'))
            except PermissionError as error:
                self.add_error('observer', str(error))
        return data


class MessageForm(forms.Form):
    message = forms.CharField(
        max_length=10000,
        label='',
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Type your message...',
                'class': 'form-control',
            }
        )
    )
