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
                'tier_type': 'free',
                'price': 0.00,
                'description': 'Try basic Nigerian recipes at no cost.',
                'features': {
                    'meal_plan_limit': 3,
                    'recipe_access': 'basic',
                    'gemini_chat': False,
                    'premium_features': False
                },
                'is_active': True,
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            },
            {
                'name': 'Pay Once',
                'tier_type': 'pay_once',
                'price': 1.99,
                'description': 'Full features for a single meal plan.',
                'features': {
                    'meal_plan_limit': 1,
                    'recipe_access': 'full',
                    'gemini_chat': False,
                    'premium_features': True
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
                    'meal_plan_limit': 0,
                    'recipe_access': 'full',
                    'gemini_chat': True,
                    'premium_features': True
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