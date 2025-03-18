# dashboard/decorators.py
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages

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