import json
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import openai

# Cache configuration
CACHE_TIMEOUTS = {
    'short': 300,        # 5 minutes
    'medium': 1800,      # 30 minutes
    'long': 3600,        # 1 hour
    'very_long': 86400,  # 24 hours
}


def recipe_image_path(instance, filename):
    base, ext = os.path.splitext(filename)
    clean_base = "".join(c for c in base if c.isalnum() or c in ('-', '_'))
    clean_filename = f"{clean_base}{ext}".lower()
    return os.path.join('recipes', str(instance.user.id), clean_filename)


class CacheModelMixin:
    """Mixin to add caching capabilities to models"""

    @classmethod
    def get_cache_key(cls, identifier):
        """Generate a cache key for an instance"""
        return f"{cls.__name__.lower()}_{identifier}"

    def invalidate_cache(self):
        """Invalidate cache for this instance"""
        cache.delete(self.get_cache_key(self.id))

class MealPlan(models.Model, CacheModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at'], name='meal_plan_user_created_idx'),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @classmethod
    def get_user_plans(cls, user_id, limit=None):
        """Get cached meal plans for a user"""
        cache_key = f"user_meal_plans_{user_id}"
        plans = cache.get(cache_key)

        if plans is None:
            plans = list(cls.objects.filter(user_id=user_id).order_by('-created_at'))
            cache.set(cache_key, plans, CACHE_TIMEOUTS['medium'])

        return plans[:limit] if limit else plans

# dashboard/models.py
class Recipe(models.Model, CacheModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    ingredients = models.TextField()
    instructions = models.TextField()
    prep_time = models.CharField(max_length=20, default='30 mins')
    cook_time = models.CharField(max_length=20, default='45 mins')
    servings = models.IntegerField(default=4)
    difficulty = models.CharField(max_length=20, default='Intermediate')
    nutrition_info = models.JSONField(default=dict, blank=True)
    tips = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_admin_recipe = models.BooleanField(default=False)
    meal_plan = models.ForeignKey('MealPlan', on_delete=models.CASCADE, null=True, blank=True)
    meal_type = models.CharField(max_length=20, null=True, blank=True)
    day_index = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['title'], name='recipe_title_idx'),
            models.Index(fields=['is_admin_recipe'], name='recipe_admin_idx'),
            models.Index(fields=['meal_plan', 'meal_type', 'day_index'], name='recipe_meal_idx'),
        ]
        unique_together = [['meal_plan', 'meal_type', 'day_index']]

    def __str__(self):
        return self.title

    @classmethod
    def get_user_recipes(cls, user_id):
        """Get cached recipes for a user"""
        cache_key = f"user_recipes_{user_id}"
        recipes = cache.get(cache_key)

        if recipes is None:
            recipes = list(cls.objects.filter(user_id=user_id)
                         .select_related('user', 'meal_plan')
                         .order_by('-created_at'))
            cache.set(cache_key, recipes, CACHE_TIMEOUTS['medium'])

        return recipes

    @classmethod
    def generate_recipe(cls, meal_name, user, meal_plan=None, meal_type=None, day_index=None):
        """Generate a recipe using AI"""
        try:
            # First check if recipe already exists
            if meal_plan and meal_type and day_index is not None:
                existing_recipe = cls.objects.filter(
                    meal_plan=meal_plan,
                    meal_type=meal_type,
                    day_index=day_index
                ).first()

                if existing_recipe:
                    return existing_recipe

            # Generate new recipe using ChatGPT
            prompt = f"""
            Generate a detailed Nigerian recipe for {meal_name} including:
            - Brief description of the dish and its origin
            - Preparation time
            - Cooking time
            - Number of servings
            - Difficulty level
            - Detailed list of ingredients with quantities
            - Step-by-step cooking instructions
            - Nutritional information per serving
            - Traditional cooking tips and variations
            Return the response as a JSON object.
            """

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert Nigerian chef."},
                    {"role": "user", "content": prompt}
                ]
            )

            recipe_data = json.loads(response.choices[0].message.content)

            # Create new recipe
            recipe = cls.objects.create(
                user=user,
                title=meal_name,
                description=recipe_data.get('description', ''),
                ingredients=recipe_data.get('ingredients', []),
                instructions=recipe_data.get('instructions', []),
                prep_time=recipe_data.get('prep_time', '30 mins'),
                cook_time=recipe_data.get('cook_time', '45 mins'),
                servings=recipe_data.get('servings', 4),
                difficulty=recipe_data.get('difficulty', 'Intermediate'),
                nutrition_info=recipe_data.get('nutrition', {}),
                tips=recipe_data.get('tips', []),
                meal_plan=meal_plan,
                meal_type=meal_type,
                day_index=day_index
            )

            # Invalidate cache
            cache.delete(f"user_recipes_{user.id}")
            if meal_plan:
                cache.delete(f"meal_plan_{meal_plan.id}")

            return recipe

        except Exception as e:
            print(f"Error generating recipe: {str(e)}")
            return None

class GroceryList(models.Model, CacheModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    items = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at'], name='grocery_user_created_idx'),
        ]

    def __str__(self):
        return f"Grocery List for {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"

    @classmethod
    def get_latest_for_user(cls, user_id):
        """Get cached latest grocery list for a user"""
        cache_key = f"latest_grocery_list_{user_id}"
        grocery_list = cache.get(cache_key)

        if grocery_list is None:
            grocery_list = cls.objects.filter(user_id=user_id).order_by('-created_at').first()
            if grocery_list:
                cache.set(cache_key, grocery_list, CACHE_TIMEOUTS['short'])

        return grocery_list

class SubscriptionTier(models.Model, CacheModelMixin):
    TIER_CHOICES = (
        ('one_time', 'Pay As You Go'),
        ('weekly', 'Weekly Plan'),
        ('monthly', 'Monthly Plan'),
    )

    name = models.CharField(max_length=100, db_index=True)
    tier_type = models.CharField(max_length=20, choices=TIER_CHOICES, db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    features = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True, db_index=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['tier_type', 'price'], name='tier_type_price_idx'),
        ]

    def __str__(self):
        return f"{self.name} (£{self.price})"

    @classmethod
    def get_active_tiers(cls):
        """Get cached active subscription tiers"""
        cache_key = "active_subscription_tiers"
        tiers = cache.get(cache_key)

        if tiers is None:
            tiers = list(cls.objects.filter(is_active=True).order_by('price'))
            cache.set(cache_key, tiers, CACHE_TIMEOUTS['long'])

        return tiers

class UserSubscription(models.Model, CacheModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    subscription_tier = models.ForeignKey(SubscriptionTier, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active', 'end_date'], name='sub_user_active_end_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.subscription_tier.name}"

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()

    @classmethod
    def get_active_subscription(cls, user_id):
        """Get cached active subscription for a user"""
        cache_key = f"active_subscription_{user_id}"
        subscription = cache.get(cache_key)

        if subscription is None:
            subscription = cls.objects.filter(
                user_id=user_id,
                is_active=True,
                end_date__gt=timezone.now()
            ).select_related('subscription_tier').first()
            if subscription:
                cache.set(cache_key, subscription, CACHE_TIMEOUTS['medium'])

        return subscription

class UserActivity(models.Model, CacheModelMixin):
    ACTION_CHOICES = (
        ('create_meal', 'Created Meal Plan'),
        ('update_meal', 'Updated Meal Plan'),
        ('delete_meal', 'Deleted Meal Plan'),
        ('create_recipe', 'Created Recipe'),
        ('update_recipe', 'Updated Recipe'),
        ('delete_recipe', 'Deleted Recipe'),
        ('subscription', 'Subscription Change'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('feedback', 'Submitted Feedback'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp}"

    @classmethod
    def log_activity(cls, user, action, details=None, request=None):
        activity_data = {
            'user': user,
            'action': action,
            'details': details or {},
        }
        
        if request:
            activity_data['ip_address'] = request.META.get('REMOTE_ADDR')
            activity_data['user_agent'] = request.META.get('HTTP_USER_AGENT')

        activity = cls.objects.create(**activity_data)
        
        # Invalidate cache
        cache_key = f"user_activity_{user.id}"
        cache.delete(cache_key)
        
        return activity

class UserFeedback(models.Model, CacheModelMixin):
    FEEDBACK_TYPES = (
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('general', 'General Feedback'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPES)
    subject = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.subject}"

# Signal handlers for cache invalidation
@receiver([post_save, post_delete], sender=MealPlan)
def invalidate_meal_plan_cache(sender, instance, **kwargs):
    cache.delete(f"user_meal_plans_{instance.user_id}")
    cache.delete(f"meal_plan_{instance.id}")

@receiver([post_save, post_delete], sender=Recipe)
def invalidate_recipe_cache(sender, instance, **kwargs):
    cache.delete(f"user_recipes_{instance.user_id}")
    cache.delete(f"recipe_{instance.id}")

@receiver([post_save, post_delete], sender=GroceryList)
def invalidate_grocery_list_cache(sender, instance, **kwargs):
    cache.delete(f"latest_grocery_list_{instance.user_id}")
    cache.delete(f"grocery_list_{instance.id}")

@receiver([post_save, post_delete], sender=SubscriptionTier)
def invalidate_subscription_tier_cache(sender, instance, **kwargs):
    cache.delete("active_subscription_tiers")

@receiver([post_save, post_delete], sender=UserSubscription)
def invalidate_user_subscription_cache(sender, instance, **kwargs):
    cache.delete(f"active_subscription_{instance.user_id}")

@receiver([post_save, post_delete], sender=UserActivity)
def invalidate_user_activity_cache(sender, instance, **kwargs):
    cache.delete(f"user_activity_{instance.user_id}")