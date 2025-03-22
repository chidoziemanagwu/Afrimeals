# dashboard/utils/subscription.py
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from ..models import UserSubscription, MealPlan

def check_subscription_access(feature):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Remove recipe_details from feature requirements
            feature_requirements = {
                'gemini_chat': ['weekly'],  # Weekly only
                'detailed_nutrition': ['weekly'],  # Weekly only
                'meal_planning': ['pay_once', 'weekly']  # Allow both
            }

            # Only check subscription for features other than recipe_details
            if feature in feature_requirements:
                subscription = UserSubscription.objects.filter(
                    user=request.user,
                    is_active=True,
                    end_date__gt=timezone.now()
                ).select_related('subscription_tier').first()

                allowed_tiers = feature_requirements[feature]

                if not subscription or subscription.subscription_tier.tier_type not in allowed_tiers:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'requires_upgrade': True,
                            'message': f'This feature requires a {"weekly" if "weekly" in allowed_tiers else "premium"} subscription'
                        }, status=403)

                    messages.warning(request, f'This feature requires a {"weekly" if "weekly" in allowed_tiers else "premium"} subscription')
                    return redirect('pricing')

            return view_func(self, request, *args, **kwargs)

        return wrapper
    return decorator