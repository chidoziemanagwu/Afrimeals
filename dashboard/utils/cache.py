# dashboard/utils/cache.py

from django.core.cache import cache
from django.conf import settings

def get_or_set_cache(key, callback, timeout=None):
    """
    Get value from cache or set it if not present
    """
    value = cache.get(key)
    if value is None:
        value = callback()
        cache.set(key, value, timeout or settings.CACHE_TIMEOUTS['medium'])
    return value

def invalidate_user_caches(user_id):
    """
    Invalidate all caches related to a user
    """
    cache_keys = [
        f"user_meal_plans_{user_id}",
        f"user_recipes_{user_id}",
        f"latest_grocery_list_{user_id}",
        f"active_subscription_{user_id}",
    ]
    cache.delete_many(cache_keys)