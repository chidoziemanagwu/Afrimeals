from django.test import TestCase
from django.contrib.auth import get_user_model
from dashboard.models import Subscription
import stripe

class SubscriptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_subscription_creation(self):
        subscription = Subscription.objects.create(
            user=self.user,
            stripe_subscription_id='sub_123',
            plan_type='WEEKLY'
        )
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.status, 'active')

    def test_subscription_cancellation(self):
        # Test subscription cancellation logic
        pass