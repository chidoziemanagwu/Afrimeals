# management/commands/create_subscription_tiers.py
from django.core.management.base import BaseCommand
from dashboard.models import SubscriptionTier
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create default subscription tiers'

    def handle(self, *args, **kwargs):
        # Delete all existing tiers
        SubscriptionTier.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Deleted existing subscription tiers'))

        tiers = [
            {
                'name': 'Free Plan',
                'tier_type': 'one_time',
                'price': 0.00,
                'description': 'Try basic Nigerian recipes at no cost.',
                'features': {
                    'Limited meal plan options': True,
                    'Basic grocery lists': True,
                    'Access to 5 popular recipes': True
                },
                'is_active': True,
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            },
            {
                'name': 'Pay Once',
                'tier_type': 'one_time',
                'price': 5.99,
                'description': 'Full features for a single meal plan.',
                'features': {
                    'Single AI-generated meal plan': True,
                    'Complete grocery list with UK prices': True,
                    'Cooking instructions with videos': True,
                    'Store location details': True
                },
                'is_active': True,
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            },
            {
                'name': 'Weekly Access',
                'tier_type': 'weekly',
                'price': 12.99,
                'description': 'Full AI assistant access for a week.',
                'features': {
                    'Unlimited meal plans for 7 days': True,
                    'Full AI cuisine assistant access': True,
                    'Advanced ingredient location finder': True,
                    'YouTube tutorial recommendations': True,
                    'Full Google Maps integration': True
                },
                'is_active': True,
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            }
        ]

        try:
            for tier_data in tiers:
                tier = SubscriptionTier.objects.create(**tier_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Created tier: {tier.name} (£{tier.price})')
                )

            self.stdout.write(
                self.style.SUCCESS('Successfully created all subscription tiers')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating subscription tiers: {str(e)}')
            )
            raise  # Re-raise the exception for proper error handling