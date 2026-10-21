from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from gyms.models import Gym, GymMembership
from parents_portal.models import ParentAthleteLink
from communications.services import create_notification
from communications.models import Notification
from practice_focus.models import EmailReportDraft
from practice_focus.email_delivery import send_report
from .models import CommunicationPreference, QueuedParentReport, ParentReportDigest
from .digests import deliver_digest


@override_settings(REPORT_EMAIL_API_KEY='test-key', REPORT_EMAIL_FROM='Gym <gym@example.com>', REPORT_EMAIL_APP_URL='https://example.com')
class CommunicationPreferencesTests(TestCase):
    def setUp(self):
        self.gym=Gym.objects.create(name='Preference Gym')
        self.parent=self.person('parent-pref','parent')
        self.child=self.person('child-pref','athlete')
        self.coach=self.person('coach-pref','head_coach')
        self.parent.email='parent@example.com';self.parent.save()
        ParentAthleteLink.objects.create(parent=self.parent,athlete=self.child,approved=True)
        self.draft=EmailReportDraft.objects.create(gym=self.gym,coach=self.coach,athlete=self.child,report_key='skill',fingerprint='abc',snapshot={'athlete_ids':[self.child.pk],'athlete_name':'Child','title':'Skill progress'})

    def person(self,name,role):
        user=get_user_model().objects.create_user(username=name,role=role)
        GymMembership.objects.create(user=user,gym=self.gym,role=role)
        return user

    def test_parent_can_save_only_own_preferences(self):
        self.client.force_login(self.parent)
        response=self.client.post(reverse('account_settings'),{'action':'communication','report_frequency':'weekly','email_reports':'on'})
        self.assertEqual(response.status_code,302)
        pref=CommunicationPreference.objects.get(user=self.parent)
        self.assertEqual(pref.report_frequency,'weekly')
        self.assertFalse(pref.in_app_updates)
        self.client.force_login(self.coach)
        self.client.post(reverse('account_settings'),{'action':'communication','report_frequency':'weekly'})
        self.assertFalse(CommunicationPreference.objects.filter(user=self.coach).exists())

    def test_in_app_optout_keeps_messages_and_system_notices(self):
        CommunicationPreference.objects.create(user=self.parent,in_app_updates=False)
        self.assertIsNone(create_notification(recipient=self.parent,title='Routine update',notification_type='achievement'))
        create_notification(recipient=self.parent,title='Message',notification_type='message')
        create_notification(recipient=self.parent,title='Account',notification_type='system')
        self.assertEqual(Notification.objects.filter(recipient=self.parent).count(),2)

    @patch('practice_focus.email_delivery.submit_email')
    def test_email_optout_and_weekly_queue_never_send_immediately(self,send):
        pref=CommunicationPreference.objects.create(user=self.parent,email_reports=False)
        send_report(self.draft,'parents',self.gym.pk,get_user_model().objects.filter(pk=self.child.pk))
        send.assert_not_called()
        pref.email_reports=True;pref.report_frequency='weekly';pref.save()
        result=send_report(self.draft,'parents',self.gym.pk,get_user_model().objects.filter(pk=self.child.pk))
        self.assertEqual(result['queued'],1);send.assert_not_called()
        self.assertEqual(QueuedParentReport.objects.count(),1)
        send_report(self.draft,'parents',self.gym.pk,get_user_model().objects.filter(pk=self.child.pk))
        self.assertEqual(QueuedParentReport.objects.count(),1)

    @patch('accounts.digests.submit_email',return_value='provider-id')
    def test_digest_sends_once_and_rechecks_revoked_access(self,send):
        CommunicationPreference.objects.create(user=self.parent,report_frequency='weekly')
        QueuedParentReport.objects.create(parent=self.parent,draft=self.draft)
        self.assertEqual(deliver_digest(self.parent.pk),'')
        self.assertEqual(send.call_count,1)
        self.assertEqual(ParentReportDigest.objects.get().status,'submitted')
        deliver_digest(self.parent.pk);self.assertEqual(send.call_count,1)
        other=EmailReportDraft.objects.create(gym=self.gym,coach=self.coach,athlete=self.child,report_key='routine',fingerprint='def',snapshot=self.draft.snapshot)
        QueuedParentReport.objects.create(parent=self.parent,draft=other)
        CommunicationPreference.objects.filter(user=self.parent).update(last_digest_at=None)
        ParentAthleteLink.objects.filter(parent=self.parent).update(approved=False)
        deliver_digest(self.parent.pk);self.assertEqual(send.call_count,1)

    @patch('accounts.digests.submit_email')
    def test_digest_retry_reuses_token_and_payload(self,send):
        from practice_focus.email_provider import EmailDeliveryError
        CommunicationPreference.objects.create(user=self.parent,report_frequency='weekly')
        QueuedParentReport.objects.create(parent=self.parent,draft=self.draft)
        send.side_effect=EmailDeliveryError('Temporary error',uncertain=True)
        self.assertEqual(deliver_digest(self.parent.pk),'Temporary error')
        first=send.call_args
        send.side_effect=None;send.return_value='ok'
        self.assertEqual(deliver_digest(self.parent.pk),'')
        self.assertEqual(first,send.call_args)
