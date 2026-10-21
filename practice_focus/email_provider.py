"""HTTPS delivery; no SMTP ports or additional packages required."""
import json
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class EmailDeliveryError(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


def email_configuration():
    key = getattr(settings, 'REPORT_EMAIL_API_KEY', '')
    sender = getattr(settings, 'REPORT_EMAIL_FROM', '')
    base_url = getattr(settings, 'REPORT_EMAIL_APP_URL', '').rstrip('/')
    if not key or not sender:
        return 'Email delivery is not configured. Set REPORT_EMAIL_API_KEY and REPORT_EMAIL_FROM on the server.'
    try:
        address = parseaddr(sender)[1]
        validate_email(address)
    except ValidationError:
        return 'The report sender email address is invalid.'
    if '\r' in sender or '\n' in sender:
        return 'The report sender email address is invalid.'
    url = urlsplit(base_url)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        return 'Set REPORT_EMAIL_APP_URL to the public HTTPS address of your app.'
    return ''


def submit_email(payload, token):
    problem = email_configuration()
    if problem:
        raise EmailDeliveryError(problem)
    request = Request('https://api.resend.com/emails', method='POST',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={
            'Authorization': 'Bearer ' + settings.REPORT_EMAIL_API_KEY,
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'User-Agent': 'NewSchoolGymnastics-Reports/1.0',
            'Idempotency-Key': 'report-email/' + str(token)})
    try:
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read(65536))
        if not isinstance(data, dict) or not isinstance(data.get('id'), str) or not data['id']:
            raise EmailDeliveryError('The provider response could not be confirmed. Retry this email.', uncertain=True)
        return data['id'][:160]
    except HTTPError as error:
        if error.code in (401, 403):
            raise EmailDeliveryError('The email provider refused the request. Check the API key and verified sender.') from None
        if error.code == 429:
            raise EmailDeliveryError('The email provider rate limit was reached. Wait a little, then retry.') from None
        if error.code == 409:
            raise EmailDeliveryError('The provider is processing this request or needs the original preview. Retry shortly.', uncertain=True) from None
        if error.code >= 500:
            raise EmailDeliveryError('The email provider is temporarily unavailable. Retry this email.', uncertain=True) from None
        raise EmailDeliveryError('The email provider rejected this message. Check the sender and recipient addresses.') from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise EmailDeliveryError('Delivery confirmation was lost. Retry this email using the same preview.', uncertain=True) from None
