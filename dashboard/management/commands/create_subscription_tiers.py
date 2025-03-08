from django.core.management.base import BaseCommand
from dashboard.models import SubscriptionTier

class Command(BaseCommand):
    help = 'Create default subscription tiers'

    def handle(self, *args, **kwargs):
        # Check if tiers already exist
        if SubscriptionTier.objects.exists():
            self.stdout.write(self.style.WARNING('Subscription tiers already exist.'))
            return

        # Create Pay-As-You-Go plan
        one_time = SubscriptionTier.objects.create(
            name='Pay As You Go',
            tier_type='one_time',
            price=9.99,
            description='Get a single meal plan without a subscription.',
            features={
                'Single meal plan generation': True,
                'Basic recipe access': True,
                'Downloadable shopping list': True,
                'No recurring commitment': True
            }
        )

        # Create Weekly plan
        weekly = SubscriptionTier.objects.create(
            name='Weekly Plan',
            tier_type='weekly',
            price=14.99,
            description='Weekly access to all NaijaPlate features.',
            features={
                '7-day access': True,
                'Up to 3 meal plan generations': True,
                'Full recipe database access': True,
                'Shopping list integration': True,
                'Basic nutritional tracking': True
            }
        )

        # Create Monthly plan
        monthly = SubscriptionTier.objects.create(
            name='Monthly Plan',
            tier_type='monthly',
            price=39.99,
            description='Our best value with unlimited access to all premium features.',
            features={
                'Full 30-day access': True,
                'Unlimited meal plan generations': True,
                'Premium recipe collection access': True,
                'Advanced nutritional analytics': True,
                'Shopping list with store integration': True,
                'Meal prep guides and substitutions': True
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully created subscription tiers.'))