from django import forms

from accounts.models import User

from .services import get_allowed_message_recipients


class NewConversationForm(forms.Form):
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
            self.fields[
                'recipient'
            ].queryset = (
                get_allowed_message_recipients(
                    user
                )
            )

        for field in self.fields.values():
            field.widget.attrs[
                'class'
            ] = 'form-control'


class MessageForm(forms.Form):
    message = forms.CharField(
        label='',
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Type your message...',
                'class': 'form-control',
            }
        )
    )