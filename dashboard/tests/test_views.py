# dashboard/tests/test_views.py
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

from dashboard.models import (
    MealPlan, Recipe, GroceryList, 
    SubscriptionTier, UserSubscription
)
from dashboard.views import (
    MealGeneratorView, CheckoutView, RecipeCreateView
)
from dashboard.forms import RecipeForm, FeedbackForm

class ViewTestMixin:
    """Mixin with common setup for view tests"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Set up test client
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Set up request factory
        self.factory = RequestFactory()

class HomeViewTest(ViewTestMixin, TestCase):
    def test_home_view_not_logged_in(self):
        """Test home view when not logged in"""
        # Logout first
        self.client.logout()
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
    
    def test_home_view_redirect_when_logged_in(self):
        """Test home view redirects to dashboard when logged in"""
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('dashboard'))

class DashboardViewTest(ViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.meal_plan = MealPlan.objects.create(
            user=self.user,
            name='Test Meal Plan',
            description='Test description'
        )
        
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            instructions='Test instructions'
        )
    
    def test_dashboard_view_requires_login(self):
        """Test dashboard view requires login"""
        # Logout first
        self.client.logout()
        
        # Try to access dashboard
        response = self.client.get(reverse('dashboard'))
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_dashboard_view_with_login(self):
        """Test dashboard view when logged in"""
        response = self.client.get(reverse('dashboard'))
        
        # Should return successful response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        
        # Should contain user's meal plans and recipes
        self.assertIn(self.meal_plan, response.context['recent_meal_plans'])
        self.assertIn(self.recipe, response.context['recent_recipes'])

class MealGeneratorViewTest(ViewTestMixin, TestCase):
    @patch('dashboard.views.MealGeneratorView._has_active_subscription')
    def test_meal_generator_get(self, mock_has_subscription):
        """Test meal generator GET view"""
        mock_has_subscription.return_value = True
        
        response = self.client.get(reverse('meal_generator'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'meal_generator.html')
        self.assertTrue(response.context['has_subscription'])
    
    @patch('dashboard.views.client.completions.create')
    @patch('dashboard.views.MealGeneratorView._has_active_subscription')
    def test_meal_generator_post(self, mock_has_subscription, mock_openai):
        """Test meal generator POST view"""
        # Mock subscription check
        mock_has_subscription.return_value = True
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].text = """MEAL PLAN:
        Day 1:
        Breakfast: Nigerian breakfast
        Lunch: Nigerian lunch
        Dinner: Nigerian dinner
        
        GROCERY LIST:
        - Item 1
        - Item 2"""
        mock_openai.return_value = mock_response
        
        # Make post request
        response = self.client.post(reverse('meal_generator'), {
            'dietary_preferences': 'balanced',
            'preferred_cuisine': 'Nigerian',
            'meals_per_day': '3',
            'plan_days': '1'
        })
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['meal_plan']), 1)  # 1 day as requested
        self.assertEqual(len(response_data['grocery_list']), 2)  # 2 items
        
        # Verify database objects were created
        self.assertTrue(MealPlan.objects.filter(user=self.user).exists())
        self.assertTrue(GroceryList.objects.filter(user=self.user).exists())
    
    @patch('dashboard.views.MealGeneratorView._has_active_subscription')
    def test_meal_generator_premium_features_without_subscription(self, mock_has_subscription):
        """Test premium features are blocked without subscription"""
        # Mock subscription check to return False
        mock_has_subscription.return_value = False
        
        # Make post request with premium features
        response = self.client.post(reverse('meal_generator'), {
            'dietary_preferences': 'balanced',
            'preferred_cuisine': 'Nigerian',
            'meals_per_day': '3',
            'plan_days': '1',
            'detailed_nutrition': 'on'  # Premium feature
        })
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertTrue(response_data['requires_upgrade'])

class CheckoutViewTest(ViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        
        # Create test subscription tier
        self.tier = SubscriptionTier.objects.create(
            name='Premium',
            tier_type='monthly',
            price=9.99,
            description='Premium subscription',
            stripe_price_id='price_123456'
        )
    
    def test_checkout_view_get(self):
        """Test checkout view GET"""
        response = self.client.get(reverse('checkout', args=[self.tier.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout.html')
        self.assertEqual(response.context['tier'], self.tier)
    
    @patch('dashboard.views.stripe.Customer.create')
    @patch('dashboard.views.stripe.Subscription.create')
    def test_checkout_view_post_monthly(self, mock_subscription, mock_customer):
        """Test checkout view POST for monthly subscription"""
        # Mock Stripe responses
        mock_customer.return_value = MagicMock(id='cus_123456')
        mock_subscription.return_value = MagicMock(id='sub_123456')
        
        # Make post request
        response = self.client.post(
            reverse('checkout', args=[self.tier.id]),
            {'stripeToken': 'tok_visa'}
        )
        
        # Verify redirect
        self.assertRedirects(response, reverse('subscription_success'))
        
        # Verify subscription was created
        self.assertTrue(UserSubscription.objects.filter(
            user=self.user,
            subscription_tier=self.tier
        ).exists())

class RecipeViewsTest(ViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        
        # Create test recipe
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            instructions='Test instructions'
        )
    
    def test_recipe_list_view(self):
        """Test recipe list view"""
        response = self.client.get(reverse('recipes'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes.html')
        self.assertIn(self.recipe, response.context['recipes'])
    
    def test_recipe_detail_view(self):
        """Test recipe detail view"""
        response = self.client.get(reverse('recipe_detail', args=[self.recipe.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_detail.html')
        self.assertEqual(response.context['recipe'], self.recipe)
    
    def test_recipe_create_view(self):
        """Test recipe create view"""
        # Get the form page
        response = self.client.get(reverse('recipe_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], RecipeForm)
        
        # Submit the form
        response = self.client.post(reverse('recipe_create'), {
           'title': 'New Recipe',
            'ingredients': 'New ingredients',
            'instructions': 'New instructions'
        })
        
        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
        
        # Recipe should exist in database
        self.assertTrue(Recipe.objects.filter(
            user=self.user,
            title='New Recipe'
        ).exists())