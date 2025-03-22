# dashboard/context_processors.py
from django.utils import timezone
from .models import MealPlan, UserSubscription


# dashboard/context_processors.py

def subscription_status(request):
    """Provide subscription information to all templates"""
    if not request.user.is_authenticated:
        return {
            'subscription': None,
            'has_subscription': False,
            'is_premium': False,
            'can_use_gemini': False,
            'has_detailed_recipes': False,
            'meal_plans_used': 0,
            'meal_plans_remaining': 3,
            'subscription_type': 'free'
        }

    subscription = UserSubscription.get_active_subscription(request.user.id)
    meal_plan_count = MealPlan.objects.filter(user=request.user).count()

    context = {
        'subscription': subscription,
        'has_subscription': subscription is not None,
        'meal_plans_used': meal_plan_count,
        'subscription_type': 'free'
    }

    if not subscription:
        context.update({
            'is_premium': False,
            'can_use_gemini': False,
            'has_detailed_recipes': False,
            'meal_plans_remaining': 3 - meal_plan_count
        })
    else:
        context.update({
            'is_premium': subscription.subscription_tier.tier_type == 'weekly',
            'can_use_gemini': subscription.subscription_tier.tier_type == 'weekly',
            'has_detailed_recipes': True,
            'meal_plans_remaining': None if subscription.subscription_tier.tier_type == 'weekly' else 1 - meal_plan_count,
            'subscription_type': subscription.subscription_tier.tier_type
        })

    return context