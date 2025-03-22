# dashboard/middleware.py

from dashboard.models import UserSubscription
from django.core.cache import cache

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if subscription info needs refresh
            subscription_cache_key = f'user_subscription_{request.user.id}'
            if not cache.get(subscription_cache_key):
                subscription = UserSubscription.get_active_subscription(request.user.id)
                if subscription:
                    cache.set(
                        subscription_cache_key,
                        subscription,
                        timeout=3600  # 1 hour
                    )

        response = self.get_response(request)
        return response