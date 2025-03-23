# dashboard/decorators.py
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib import messages

from afrimeals_project import settings
from .models import UserSubscription, MealPlan

from django.utils import timezone
from django.shortcuts import render, redirect
import time

def rate_limit(key_prefix, max_requests=5, timeout=3600, burst_limit=2):
    """Enhanced rate limit decorator with burst protection and user-based limits

    Args:
        key_prefix (str): Identifier for the rate limited endpoint
        max_requests (int): Maximum number of requests allowed in the timeout period
        timeout (int): Period (in seconds) for rate limiting
        burst_limit (int): Maximum requests allowed within 1 second
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            try:
                # Get client IP
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

                # Create cache keys
                user_key = f"{key_prefix}_{request.user.id}"
                burst_key = f"{user_key}_burst"
                ip_key = f"{key_prefix}_ip_{ip}"

                # Check burst limit (requests within 1 second)
                burst_count = cache.get(burst_key, 0)
                if burst_count >= burst_limit:
                    return handle_rate_limit_exceeded(
                        request,
                        "Too many requests too quickly. Please wait a moment."
                    )
                cache.set(burst_key, burst_count + 1, 1)

                # Get user's subscription type and adjust limits
                subscription = UserSubscription.get_active_subscription(request.user.id)
                limits = {
                    'free': max_requests,
                    'pay_once': max_requests * 2,
                    'weekly': max_requests * 4,
                    'staff': max_requests * 10
                }

                user_type = (
                    'staff' if request.user.is_staff
                    else subscription.subscription_tier.tier_type if subscription
                    else 'free'
                )
                adjusted_max_requests = limits.get(user_type, max_requests)

                # Get list of request timestamps
                requests = cache.get(user_key, [])
                now = timezone.now()

                # Clean old requests outside the window
                requests = [req for req in requests
                          if (now - req).total_seconds() < timeout]

                # Check if rate limit is exceeded
                if len(requests) >= adjusted_max_requests:
                    wait_time = timeout - (now - requests[0]).total_seconds()
                    return handle_rate_limit_exceeded(
                        request,
                        f"Rate limit exceeded. Please try again in {int(wait_time/60)} minutes.",
                        wait_time
                    )

                # Add current request timestamp
                requests.append(now)
                cache.set(user_key, requests, timeout)

                # Execute view and add rate limit headers
                response = view_func(self, request, *args, **kwargs)

                # Add rate limit headers if it's a JsonResponse
                if isinstance(response, JsonResponse):
                    response['X-RateLimit-Limit'] = str(adjusted_max_requests)
                    response['X-RateLimit-Remaining'] = str(adjusted_max_requests - len(requests))
                    response['X-RateLimit-Reset'] = str(int(time.time() + timeout))

                return response

            except Exception as e:
                # Log the error here
                return handle_rate_limit_exceeded(
                    request,
                    "An error occurred while checking rate limit."
                )

        return _wrapped_view
    return decorator

def handle_rate_limit_exceeded(request, message, wait_time=None):
    """Handle rate limit exceeded cases"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': False,
            'error': message
        }
        if wait_time:
            response_data['retry_after'] = int(wait_time)
        return JsonResponse(response_data, status=429)
    else:
        messages.error(request, message)
        return redirect('home')



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