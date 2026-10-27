from uuid import uuid4
from unittest.mock import patch
from html import unescape
import re

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import Client, TestCase
from django.urls import reverse

from .enquiry_forms import TOKEN_SALT
from .models import PublicEnquiry


class PublicEnquiryTests(TestCase):
    def data(self, **changes):
        return {
            'name': 'Sample Director', 'email': 'director@example.com',
            'gym_name': 'Example Gym', 'kind': 'demo', 'message': 'Show us the coaching workflow.',
            'consent_to_reply': 'on',
            'submission_token': signing.dumps(str(uuid4()), salt=TOKEN_SALT),
            **changes,
        }

    @patch('django.core.mail.send_mail')
    def test_anonymous_request_is_saved_without_creating_accounts_or_sending_email(self, send_mail):
        count = get_user_model().objects.count()
        response = self.client.post(reverse('public_demo'), self.data())
        self.assertRedirects(response, reverse('public_enquiry_received'))
        self.assertEqual(PublicEnquiry.objects.get().email, 'director@example.com')
        self.assertEqual(get_user_model().objects.count(), count)
        send_mail.assert_not_called()
        self.assertNotContains(self.client.get(reverse('public_enquiry_received')), 'director@example.com')

    def test_retry_is_idempotent_and_cannot_overwrite_an_existing_request(self):
        data = self.data()
        self.client.post(reverse('public_demo'), data)
        data['email'] = 'different@example.com'
        self.client.post(reverse('public_demo'), data)
        self.assertEqual(PublicEnquiry.objects.count(), 1)
        self.assertEqual(PublicEnquiry.objects.get().email, 'director@example.com')

    def test_invalid_fields_and_unsigned_tokens_are_not_stored(self):
        for changes in [
            {'email': 'invalid'}, {'consent_to_reply': ''}, {'kind': 'admin'},
            {'submission_token': str(uuid4())}, {'website': 'https://spam.example.com'},
            {'message': 'x' * 2001},
        ]:
            with self.subTest(changes=changes.keys()):
                response = self.client.post(reverse('public_demo'), self.data(**changes))
                self.assertContains(response, 'Please check the form.')
        self.assertEqual(PublicEnquiry.objects.count(), 0)

    def test_expired_tokens_are_not_stored(self):
        with patch('django.core.signing.time.time', return_value=1):
            data = self.data()
        self.client.post(reverse('public_demo'), data)
        self.assertEqual(PublicEnquiry.objects.count(), 0)

    def test_session_submission_limit_and_successful_retry(self):
        data = self.data()
        for _ in range(3):
            self.assertEqual(self.client.post(reverse('public_demo'), self.data()).status_code, 302)
        self.assertEqual(self.client.post(reverse('public_demo'), data).status_code, 429)
        self.assertEqual(PublicEnquiry.objects.count(), 3)
        session = self.client.session
        session['public_enquiry_times'] = [1]
        session.save()
        self.assertEqual(self.client.post(reverse('public_demo'), data).status_code, 302)
        self.assertEqual(PublicEnquiry.objects.count(), 4)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('public_demo'), self.data()).status_code, 403)
        self.assertEqual(PublicEnquiry.objects.count(), 0)

    def test_rendered_form_can_submit_with_csrf_protection_enabled(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse('public_demo'))
        html = response.content.decode()
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)[1]
        token = re.search(r'name="submission_token" value="([^"]+)"', html)[1]
        response = client.post(reverse('public_demo'), self.data(
            csrfmiddlewaretoken=unescape(csrf), submission_token=unescape(token),
        ))
        self.assertRedirects(response, reverse('public_enquiry_received'))
        self.assertEqual(PublicEnquiry.objects.count(), 1)

    def test_contact_topic_and_anonymous_pages(self):
        response = self.client.get(reverse('public_contact'), {'topic': 'privacy'})
        self.assertEqual(response.context['form'].initial['kind'], 'privacy')
        for name in ['home', 'public_demo', 'public_pricing', 'public_features', 'public_privacy', 'public_support']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, reverse('public_demo'))
        self.assertContains(self.client.get(reverse('public_privacy')), 'not a completed privacy policy')


class ProductInboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.director = User.objects.create_user(username='director', role='director')
        cls.staff = User.objects.create_user(username='staff', role='admin', is_staff=True)
        cls.owner = User.objects.create_superuser(username='owner', email='owner@example.com', role='admin')
        cls.enquiry = PublicEnquiry.objects.create(
            name='Director', email='director@example.com', kind='demo', consent_to_reply=True,
            message='<script>alert("private")</script>',
        )

    def test_only_active_platform_superusers_can_read_or_change_enquiries(self):
        url = reverse('public_enquiry_inbox')
        self.assertEqual(self.client.get(url).status_code, 302)
        for user in [self.director, self.staff]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {'enquiry_id': self.enquiry.pk, 'status': 'closed'}).status_code, 403)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'new')
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertContains(response, 'director@example.com')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertRedirects(self.client.post(url, {'enquiry_id': self.enquiry.pk, 'status': 'contacted'}), url)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'contacted')

    def test_inbox_rejects_invalid_status_and_ids(self):
        self.client.force_login(self.owner)
        url = reverse('public_enquiry_inbox')
        self.assertEqual(self.client.post(url, {'enquiry_id': 'invalid', 'status': 'closed'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'enquiry_id': self.enquiry.pk, 'status': 'invalid'}).status_code, 400)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'new')

    def test_public_pages_never_render_lead_details(self):
        for name in ['home', 'public_demo', 'public_contact', 'public_enquiry_received']:
            response = self.client.get(reverse(name))
            self.assertNotContains(response, 'director@example.com')
