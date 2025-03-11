# dashboard/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.models import (
    Recipe, MealPlan, GroceryList,
    SubscriptionTier, UserSubscription,
    UserActivity, UserFeedback
)
from datetime import timedelta
from django.core.cache import cache

class ModelBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user
        cls.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create second test user for isolation tests
        cls.test_user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpassword'
        )

class RecipeModelTest(ModelBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create test recipes
        cls.recipe1 = Recipe.objects.create(
            user=cls.test_user,
            title='Test Recipe 1',
            ingredients='Ingredient 1\nIngredient 2',
            instructions='Step 1\nStep 2'
        )

        cls.recipe2 = Recipe.objects.create(
            user=cls.test_user,
            title='Test Recipe 2',
            ingredients='Ingredient A\nIngredient B',
            instructions='Step A\nStep B'
        )

        # Create recipe for second user
        cls.other_recipe = Recipe.objects.create(
            user=cls.test_user2,
            title='Other User Recipe',
            ingredients='Other Ingredient',
            instructions='Other Instructions'
        )

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def test_recipe_creation(self):
        """Test that recipes are created correctly"""
        self.assertEqual(self.recipe1.title, 'Test Recipe 1')
        self.assertEqual(self.recipe1.ingredients, 'Ingredient 1\nIngredient 2')
        self.assertEqual(self.recipe1.instructions, 'Step 1\nStep 2')
        self.assertEqual(self.recipe1.user, self.test_user)

    def test_recipe_str_method(self):
        """Test string representation"""
        self.assertEqual(str(self.recipe1), 'Test Recipe 1')

    def test_get_user_recipes(self):
        """Test get_user_recipes method returns only user's recipes"""
        recipes = Recipe.get_user_recipes(self.test_user.id)

        # Should return both recipes for test_user
        self.assertEqual(len(recipes), 2)

        # Should contain both test recipes
        recipe_titles = [recipe.title for recipe in recipes]
        self.assertIn('Test Recipe 1', recipe_titles)
        self.assertIn('Test Recipe 2', recipe_titles)

        # Should not contain other user's recipe
        self.assertNotIn('Other User Recipe', recipe_titles)

    def test_get_user_recipes_caching(self):
        """Test that get_user_recipes uses and updates cache"""
        # First call should cache the results
        recipes_first_call = Recipe.get_user_recipes(self.test_user.id)

        # Verify cache is set
        cache_key = f"user_recipes_{self.test_user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Add a new recipe - this should not appear in cached results
        Recipe.objects.create(
            user=self.test_user,
            title='New Recipe During Test',
            ingredients='New Ingredients',
            instructions='New Instructions'
        )

        # Second call should use cache and not include new recipe
        recipes_second_call = Recipe.get_user_recipes(self.test_user.id)
        self.assertEqual(len(recipes_first_call), len(recipes_second_call))

        # After invalidating cache, should get updated results
        cache.delete(cache_key)
        recipes_after_invalidation = Recipe.get_user_recipes(self.test_user.id)
        self.assertEqual(len(recipes_after_invalidation), 3)

        # Verify new recipe is in the results
        new_recipe_titles = [recipe.title for recipe in recipes_after_invalidation]
        self.assertIn('New Recipe During Test', new_recipe_titles)

class MealPlanModelTest(ModelBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create test meal plans
        cls.meal_plan1 = MealPlan.objects.create(
            user=cls.test_user,
            name='Weekly Plan',
            description='Meal plan for the week'
        )

        cls.meal_plan2 = MealPlan.objects.create(
            user=cls.test_user,
            name='Special Diet Plan',
            description='Low carb plan'
        )

        # Create meal plan for second user
        cls.other_meal_plan = MealPlan.objects.create(
            user=cls.test_user2,
            name='Other User Plan',
            description='Another plan'
        )

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def test_meal_plan_creation(self):
        """Test that meal plans are created correctly"""
        self.assertEqual(self.meal_plan1.name, 'Weekly Plan')
        self.assertEqual(self.meal_plan1.description, 'Meal plan for the week')
        self.assertEqual(self.meal_plan1.user, self.test_user)

    def test_meal_plan_str_method(self):
        """Test string representation"""
        expected = f"Weekly Plan - {self.test_user.username}"
        self.assertEqual(str(self.meal_plan1), expected)

    def test_get_user_plans(self):
        """Test get_user_plans method returns only user's meal plans"""
        plans = MealPlan.get_user_plans(self.test_user.id)

        # Should return both plans for test_user
        self.assertEqual(len(plans), 2)

        # Should contain both test plans
        plan_names = [plan.name for plan in plans]
        self.assertIn('Weekly Plan', plan_names)
        self.assertIn('Special Diet Plan', plan_names)

        # Should not contain other user's plan
        self.assertNotIn('Other User Plan', plan_names)

    def test_get_user_plans_with_limit(self):
        """Test get_user_plans respects the limit parameter"""
        plans = MealPlan.get_user_plans(self.test_user.id, limit=1)
        self.assertEqual(len(plans), 1)

class SubscriptionModelTest(ModelBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create subscription tiers
        cls.free_tier = SubscriptionTier.objects.create(
            name='Free',
            tier_type='one_time',
            price=0.00,
            description='Free tier',
            features={'recipe_limit': 5}
        )

        cls.premium_tier = SubscriptionTier.objects.create(
            name='Premium',
            tier_type='monthly',
            price=9.99,
            description='Premium tier',
            features={'recipe_limit': 100, 'advanced_features': True},
            stripe_price_id='price_123456'
        )

        # Create user subscription
        cls.subscription = UserSubscription.objects.create(
            user=cls.test_user,
            subscription_tier=cls.premium_tier,
            end_date=timezone.now() + timedelta(days=30),
            payment_id='test_payment_123'
        )

        # Create expired subscription
        cls.expired_subscription = UserSubscription.objects.create(
            user=cls.test_user2,
            subscription_tier=cls.premium_tier,
            end_date=timezone.now() - timedelta(days=1),
            payment_id='expired_payment_123'
        )

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def test_subscription_tier_creation(self):
        """Test that subscription tiers are created correctly"""
        self.assertEqual(self.premium_tier.name, 'Premium')
        self.assertEqual(self.premium_tier.price, 9.99)
        self.assertEqual(self.premium_tier.stripe_price_id, 'price_123456')
        self.assertEqual(self.premium_tier.features['recipe_limit'], 100)

    def test_subscription_tier_str_method(self):
        """Test string representation of subscription tier"""
        self.assertEqual(str(self.premium_tier), 'Premium (£9.99)')

    def test_user_subscription_creation(self):
        """Test that user subscriptions are created correctly"""
        self.assertEqual(self.subscription.user, self.test_user)
        self.assertEqual(self.subscription.subscription_tier, self.premium_tier)
        self.assertTrue(self.subscription.is_active)

    def test_subscription_is_valid(self):
        """Test is_valid method correctly determines validity"""
        self.assertTrue(self.subscription.is_valid())
        self.assertFalse(self.expired_subscription.is_valid())

    def test_get_active_subscription(self):
        """Test get_active_subscription returns only valid subscriptions"""
        # Should find active subscription
        subscription = UserSubscription.get_active_subscription(self.test_user.id)
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.id, self.subscription.id)

        # Should not find expired subscription
        expired = UserSubscription.get_active_subscription(self.test_user2.id)
        self.assertIsNone(expired)