# dashboard/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import MealPlan, Recipe, SubscriptionTier, UserSubscription
from django.utils import timezone
from datetime import timedelta

class ViewsTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create subscription tier
        self.tier = SubscriptionTier.objects.create(
            name='Test Tier',
            tier_type='monthly',
            price=9.99,
            description='Test description'
        )

        # Create meal plan
        self.meal_plan = MealPlan.objects.create(
            user=self.user,
            name='Test Meal Plan',
            description='Test description'
        )

        # Create client
        self.client = Client()

    def test_home_view_redirect(self):
        # Login
        self.client.login(username='testuser', password='testpassword')

        # Test redirect to dashboard
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_dashboard_view(self):
        # Login
        self.client.login(username='testuser', password='testpassword')

        # Test dashboard access
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_meal_generator_view(self):
        # Login
        self.client.login(username='testuser', password='testpassword')

        # Test meal generator access
        response = self.client.get(reverse('meal_generator'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'meal_generator.html')