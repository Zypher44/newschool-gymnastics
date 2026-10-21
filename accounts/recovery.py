"""Account recovery through the same HTTPS provider used by report delivery."""
import hashlib
import uuid

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.urls import reverse_lazy
from django.utils.html import format_html

from practice_focus.email_provider import email_configuration, submit_email, EmailDeliveryError


class AccountRecoveryForm(PasswordResetForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control', 'autocomplete': 'username',
    }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'email'})

    def get_users(self, email):
        # Family members may share an email; reset only the requested account.
        return (user for user in super().get_users(email)
                if user.username == self.cleaned_data['username'])

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        base_url = settings.REPORT_EMAIL_APP_URL.rstrip('/')
        from django.urls import reverse
        path = reverse('password_reset_confirm', kwargs={
            'uidb64': context['uid'], 'token': context['token'],
        })
        url = base_url + path
        payload = {'from': settings.REPORT_EMAIL_FROM, 'to': [to_email],
            'subject': 'Reset your NewSchool Gymnastics password',
            'text': f'A password reset was requested for {context["user"].username}. Reset it here: {url}\nIf you did not request this, you can ignore this email.',
            'html': str(format_html('<p>A password reset was requested for <strong>{}</strong>.</p><p><a href="{}">Reset your password</a></p><p>If you did not request this, you can ignore this email.</p>', context['user'].username, url))}
        submit_email(payload, 'password-reset-' + str(uuid.uuid4()))


class AccountRecoveryView(PasswordResetView):
    form_class = AccountRecoveryForm
    template_name = 'registration/account_recovery.html'
    success_url = reverse_lazy('password_reset_done')

    def get_context_data(self, **kwargs):
        return super().get_context_data(recovery_available=not bool(email_configuration()), **kwargs)

    def form_valid(self, form):
        if email_configuration():
            return self.render_to_response(self.get_context_data(form=form))
        # Do not trust forwarded IP headers. A shared cache is required when
        # running multiple app processes; this also limits the single-worker pilot.
        keys = [hashlib.sha256(value.encode()).hexdigest() for value in (
            'ip:' + self.request.META.get('REMOTE_ADDR', ''),
            'account:' + form.cleaned_data['username'],
        )]
        allowed = True
        for key in keys:
            key = 'account-recovery:' + key
            if cache.add(key, 1, 900):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, 900)
                    count = 1
            allowed = allowed and count <= 5
        if allowed:
            try:
                form.save(request=self.request, use_https=True)
            except EmailDeliveryError:
                # Never expose account existence, provider credentials, or tokens.
                pass
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())
