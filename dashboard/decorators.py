# dashboard/decorators.py
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages

def rate_limit(key_prefix, max_requests, timeout):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # Create a unique cache key for this user and endpoint
            cache_key = f"{key_prefix}_{request.user.id}"
            request_count = cache.get(cache_key, 0)

            # Check if rate limit is exceeded
            if request_count >= max_requests:
                if request.is_ajax() or request.content_type == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': 'Rate limit exceeded. Please try again later.'
                    }, status=429)
                else:
                    messages.error(request, 'Too many attempts. Please try again later.')
                    return render(request, 'rate_limit_exceeded.html', status=429)

            # Increment the counter
            cache.set(cache_key, request_count + 1, timeout)

            return view_func(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator