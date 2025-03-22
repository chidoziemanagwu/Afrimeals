# management/commands/check_expired_subscriptions.py

from django.core.management.base import BaseCommand
from dashboard.models import UserSubscription

class Command(BaseCommand):
    help = 'Check and expire weekly subscriptions that have reached their end date'

    def handle(self, *args, **options):
        expired_count = UserSubscription.check_all_active_weekly_subscriptions()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully expired {expired_count} weekly subscriptions')
        )