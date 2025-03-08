from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Existing models
class MealPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    ingredients = models.TextField()
    instructions = models.TextField()

class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.TextField()

# New subscription models
class SubscriptionTier(models.Model):
    TIER_CHOICES = (
        ('one_time', 'Pay As You Go'),
        ('weekly', 'Weekly Plan'),
        ('monthly', 'Monthly Plan'),
    )

    name = models.CharField(max_length=100)
    tier_type = models.CharField(max_length=20, choices=TIER_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    features = models.JSONField(default=dict)  # Store features as JSON

    def __str__(self):
        return f"{self.name} (£{self.price})"

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription_tier = models.ForeignKey(SubscriptionTier, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()

    def __str__(self):
        return f"{self.user.email} - {self.subscription_tier.name}"