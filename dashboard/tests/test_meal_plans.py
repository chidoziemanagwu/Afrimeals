from django.test import TestCase
from django.contrib.auth import get_user_model
from dashboard.models import Subscription
import stripe


class MealPlanGenerationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_meal_plan_generation(self):
        # Test meal plan generation
        response = self.client.post('/api/generate-meal-plan/', {
            'preferences': ['Nigerian', 'Vegetarian'],
            'days': 7
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('meal_plan', response.json())