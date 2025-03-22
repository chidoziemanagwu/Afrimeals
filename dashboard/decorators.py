# dashboard/decorators.py
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib import messages

from afrimeals_project import settings
from .models import UserSubscription, MealPlan

from django.utils import timezone

# dashboard/decorators.py

def check_subscription_limits(view_func):
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        subscription = UserSubscription.get_active_subscription(request.user.id)
        meal_plan_count = MealPlan.objects.filter(user=request.user).count()

        # Free tier limit (3 meal plans)
        if not subscription and meal_plan_count >= 3:
            return JsonResponse({
                'success': False,
                'requires_upgrade': True,
                'message': 'You have reached your free limit of 3 meal plans. Please upgrade to continue.'
            })

        # Pay Once tier limit (1 meal plan)
        if subscription and subscription.subscription_tier.tier_type == 'pay_once':
            if meal_plan_count >= 1:
                return JsonResponse({
                    'success': False,
                    'requires_upgrade': True,
                    'message': 'You have used your single meal plan generation. Please upgrade to weekly for unlimited plans.'
                })

        return view_func(self, request, *args, **kwargs)
    return _wrapped_view



def rate_limit(key_prefix, max_requests=5, timeout=3600):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # Create a unique cache key for this user and endpoint
            cache_key = f"{key_prefix}_{request.user.id}"
            request_count = cache.get(cache_key, 0)

            # Check if rate limit is exceeded
            if request_count >= max_requests:
                # Check if request is AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Rate limit exceeded. Please try again later.'
                    }, status=429)
                else:
                    messages.error(request, 'Too many attempts. Please try again later.')
                    return redirect('home')

            # Increment the request count
            cache.set(cache_key, request_count + 1, timeout)

            return view_func(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator


def check_subscription_access(feature):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            try:
                subscription = UserSubscription.objects.filter(
                    user=request.user,
                    is_active=True,
                    end_date__gt=timezone.now()
                ).select_related('subscription_tier').first()

                # Define feature access levels
                feature_requirements = {
                    'recipe_details': ['pay_once', 'weekly'],  # Allow both pay_once and weekly
                    'gemini_chat': ['weekly'],  # Weekly only
                    'detailed_nutrition': ['weekly'],  # Weekly only
                    'meal_planning': ['pay_once', 'weekly']  # Allow both
                }

                # Check if feature requires subscription
                if feature in feature_requirements:
                    allowed_tiers = feature_requirements[feature]

                    if not subscription:
                        return JsonResponse({
                            'success': False,
                            'requires_upgrade': True,
                            'message': 'Please upgrade to access detailed recipes.'
                        }, status=403)

                    if subscription.subscription_tier.tier_type not in allowed_tiers:
                        return JsonResponse({
                            'success': False,
                            'requires_upgrade': True,
                            'message': f'This feature requires a {"weekly" if "weekly" in allowed_tiers else "premium"} subscription'
                        }, status=403)

                return view_func(self, request, *args, **kwargs)

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e) if settings.DEBUG else 'An error occurred'
                }, status=500)

        return wrapper
    return decorator