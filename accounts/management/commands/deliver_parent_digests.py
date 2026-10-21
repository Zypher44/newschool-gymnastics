from django.core.management.base import BaseCommand, CommandError
from accounts.models import CommunicationPreference
from accounts.digests import deliver_digest
from practice_focus.email_provider import email_configuration

class Command(BaseCommand):
    help = 'Deliver due parent weekly summaries. Run daily using the configured scheduler after email is enabled.'
    def handle(self, *args, **options):
        if email_configuration(): raise CommandError(email_configuration())
        for pk in CommunicationPreference.objects.filter(user__is_active=True, user__role='parent', email_reports=True, report_frequency='weekly').values_list('user_id', flat=True):
            issue = deliver_digest(pk)
            if issue: self.stderr.write(f'Parent {pk}: {issue}')
