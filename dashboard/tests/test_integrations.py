# dashboard/tests/test_integrations.py
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from dashboard.models import SubscriptionTier, MealPlan, GroceryList
from dashboard.tasks import generate_meal_plan_async
import stripe
import json

class OpenAIIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    @patch('dashboard.tasks.client.completions.create')
    def test_meal_plan_generation(self, mock_openai):
        """Test meal plan generation with OpenAI"""
        # Setup mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].text = """MEAL PLAN:
        Day 1:
        Breakfast: Jollof rice with fried eggs
        Lunch: Egusi soup with pounded yam
        Dinner: Suya with plantains

        GROCERY LIST:
        - Rice
        - Eggs
        - Tomatoes
        - Egusi seeds
        - Beef
        - Plantains"""
        mock_openai.return_value = mock_response

        # Test form data
        form_data = {
            'dietary_preferences': 'Nigerian',
            'preferred_cuisine': 'West African',
            'meals_per_day': '3',
            'include_snacks': False,
            'plan_days': '1',
            'budget': 'moderate',
            'skill_level': 'Intermediate',
            'family_size': '4'
        }

        # Call the task directly
        result = generate_meal_plan_async(self.user.id, form_data)

        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('meal_plan_id', result)
        self.assertIn('grocery_list', result)

        # Verify database objects
        self.assertTrue(MealPlan.objects.filter(user=self.user).exists())
        self.assertTrue(GroceryList.objects.filter(user=self.user).exists())

        # Verify OpenAI was called with expected parameters
        mock_openai.assert_called_once()
        call_args = mock_openai.call_args[1]
        self.assertEqual(call_args['model'], 'gpt-3.5-turbo-instruct')
        self.assertIn('Nigerian', call_args['prompt'])
        self.assertIn('West African', call_args['prompt'])

class StripeIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create subscription tier
        cls.tier = SubscriptionTier.objects.create(
            name='Premium',
            tier_type='monthly',
            price=9.99,
            description='Premium features',
            stripe_price_id='price_123456'
        )

    @patch('stripe.Customer.create')
    @patch('stripe.Subscription.create')
    def test_subscription_creation(self, mock_subscription, mock_customer):
        """Test Stripe subscription creation"""
        # Mock Stripe responses
        mock_customer.return_value = MagicMock(id='cus_123456')
        mock_subscription.return_value = MagicMock(id='sub_123456')

        # Create client and login
        self.client.login(username='testuser', password='testpassword')

        # Make checkout request
        response = self.client.post(
            f'/checkout/{self.tier.id}/',
            {'stripeToken': 'tok_visa'}
        )

        # Verify redirects to success page
        self.assertRedirects(response, '/subscription-success/')

        # Verify Stripe API calls
        mock_customer.assert_called_once_with(
            email='test@example.com',
            source='tok_visa'
        )

        mock_subscription.assert_called_once()
        subscription_args = mock_subscription.call_args[1]
        self.assertEqual(subscription_args['customer'], 'cus_123456')
        self.assertEqual(
            subscription_args['items'][0]['price'],
            'price_123456'
        )

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_one_time_payment(self, mock_charge, mock_customer):
        """Test Stripe one-time payment"""
        # Update tier to one-time
        self.tier.tier_type = 'one_time'
        self.tier.save()

        # Mock Stripe responses
        mock_customer.return_value = MagicMock(id='cus_123456')
        mock_charge.return_value = MagicMock(id='ch_123456')

        # Create client and login
        self.client.login(username='testuser', password='testpassword')

        # Make checkout request
        response = self.client.post(
            f'/checkout/{self.tier.id}/',
            {'stripeToken': 'tok_visa'}
        )

        # Verify redirects to success page
        self.assertRedirects(response, '/subscription-success/')

        # Verify Stripe API calls
        mock_charge.assert_called_once()
        charge_args = mock_charge.call_args[1]
        self.assertEqual(charge_args['customer'], 'cus_123456')
        self.assertEqual(charge_args['amount'], 999)  # $9.99 in cents
        self.assertEqual(charge_args['currency'], 'gbp')