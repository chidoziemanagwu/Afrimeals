from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Improved MealPlan model with indexes
class MealPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at'], name='meal_plan_user_created_idx'),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.username}"

# Improved Recipe model with indexes
class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=100, db_index=True)
    ingredients = models.TextField()
    instructions = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)  # Removed auto_now_add

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at'], name='recipe_user_created_idx'),
        ]

    def __str__(self):
        return self.title

# Improved GroceryList model
class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    items = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)  # Removed auto_now_add

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at'], name='grocery_user_created_idx'),
        ]

    def __str__(self):
        return f"Grocery List for {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"

# Improved SubscriptionTier model
class SubscriptionTier(models.Model):
    TIER_CHOICES = (
        ('one_time', 'Pay As You Go'),
        ('weekly', 'Weekly Plan'),
        ('monthly', 'Monthly Plan'),
    )

    name = models.CharField(max_length=100, db_index=True)
    tier_type = models.CharField(max_length=20, choices=TIER_CHOICES, db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    features = models.JSONField(default=dict)  # Store features as JSON
    is_active = models.BooleanField(default=True, db_index=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['tier_type', 'price'], name='tier_type_price_idx'),
        ]

    def __str__(self):
        return f"{self.name} (£{self.price})"

# Improved UserSubscription model
class UserSubscription(models.Model):
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

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()

    def __str__(self):
        return f"{self.user.email} - {self.subscription_tier.name}"




# dashboard/models.py
class UserActivity(models.Model):
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create_meal', 'Created Meal Plan'),
        ('create_recipe', 'Created Recipe'),
        ('subscription', 'Changed Subscription'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action'], name='user_action_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp}"
    

# dashboard/models.py
class UserFeedback(models.Model):
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