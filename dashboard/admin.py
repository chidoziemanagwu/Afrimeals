from django.contrib import admin
from .models import MealPlan, Recipe, GroceryList, SubscriptionTier, UserSubscription

class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier_type', 'price')
    search_fields = ('name',)

class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_tier', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'subscription_tier')
    search_fields = ('user__email',)

admin.site.register(MealPlan)
admin.site.register(Recipe)
admin.site.register(GroceryList)
admin.site.register(SubscriptionTier, SubscriptionTierAdmin)
admin.site.register(UserSubscription, UserSubscriptionAdmin)