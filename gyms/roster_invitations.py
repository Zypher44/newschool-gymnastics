from datetime import timedelta
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.html import format_html
from .models import RosterInvitation, GymMembership
from practice_focus.email_provider import email_configuration, submit_email, EmailDeliveryError
from practice_focus.email_delivery import valid_address


class RosterPasswordSetup(PasswordResetConfirmView):
    template_name='gyms/roster_password_setup.html'
    def get_success_url(self):return reverse('login')
    def get_user(self, uidb64):
        user=super().get_user(uidb64)
        if user and (not user.is_active or user.is_staff or user.is_superuser or user.role not in ('parent','athlete','coach','head_coach')):return None
        if user and not user.roster_imports.filter(status='applied',gym__memberships__user=user,gym__memberships__is_active=True).exists():return None
        return user



def eligible_setup_user(batch,user):
    return (user.is_active and not user.is_staff and not user.is_superuser and not user.has_usable_password()
        and user.role in ('athlete','parent','coach','head_coach')
        and GymMembership.objects.filter(gym=batch.gym,user=user,role=user.role,is_active=True).exists()
        and not GymMembership.objects.filter(user=user,is_active=True).exclude(gym=batch.gym).exists())


def password_setup_path(user):
    return reverse('roster_password_setup',kwargs={'uidb64':urlsafe_base64_encode(force_bytes(user.pk)),
        'token':default_token_generator.make_token(user)})


def send_invitations(batch):
    issue=email_configuration()
    if issue:return {'sent':0,'error':'Email is not enabled yet. The accounts are ready; send invitations after email is configured.'}
    sent=0;errors=[];attempts=0
    for user in batch.created_users.order_by('pk'):
        if attempts>=2:break
        if not eligible_setup_user(batch,user):continue
        if not valid_address(user.email):continue
        with transaction.atomic():
            type(batch).objects.select_for_update().get(pk=batch.pk)
            invitation,_=RosterInvitation.objects.get_or_create(batch=batch,user=user)
            if invitation.status in ('sent','blocked'):continue
            now=timezone.now()
            if invitation.status=='sending' and invitation.last_attempt and now-invitation.last_attempt<timedelta(minutes=2):continue
            if invitation.first_attempt and now-invitation.first_attempt>timedelta(hours=23):
                invitation.status='blocked';invitation.last_error='Invitation confirmation expired. Review delivery before resending.';invitation.save();errors.append(invitation.last_error);continue
            if invitation.payload and invitation.payload.get('to') != [user.email]:
                invitation.status='blocked';invitation.last_error='Email address changed. Review this invitation.';invitation.save();errors.append(invitation.last_error);continue
            if not invitation.payload:
                path=password_setup_path(user)
                url=settings.REPORT_EMAIL_APP_URL.rstrip('/')+path
                invitation.payload={'from':settings.REPORT_EMAIL_FROM,'to':[user.email],
                    'subject':f'Your {batch.gym.name} account is ready'.replace('\r',' ').replace('\n',' ')[:250],
                    'text':f'Your username is {user.username}. Set your password: {url}',
                    'html':str(format_html('<p>Your username is <strong>{}</strong>.</p><p><a href="{}">Set your password</a> to join {}.</p>',user.username,url,batch.gym.name))}
            invitation.first_attempt=invitation.first_attempt or now;invitation.last_attempt=now
            invitation.status='sending';invitation.save()
        attempts+=1
        try:submit_email(invitation.payload,invitation.token)
        except EmailDeliveryError as error:
            RosterInvitation.objects.filter(pk=invitation.pk).update(status='failed',last_error=str(error));errors.append(str(error))
        else:
            RosterInvitation.objects.filter(pk=invitation.pk).update(status='sent',last_error='');sent+=1
    return {'sent':sent,'error':' '.join(dict.fromkeys(errors))}
