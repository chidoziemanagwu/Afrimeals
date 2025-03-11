# dashboard/tests/test_utils.py
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import RequestFactory
from unittest.mock import patch, MagicMock

from dashboard.utils.cache import get_cached_data, set_cached_data
from dashboard.decorators import rate_limit

class CacheUtilsTest(TestCase):
    def setUp(self):
        # Clear cache
        cache.clear()

    def test_get_cached_data(self):
        """Test get_cached_data function"""
        # Set test data in cache
        cache.set('test_key', 'test_value', 60)

        # Get data with function
        data = get_cached_data('test_key')
        self.assertEqual(data, 'test_value')

        # Get non-existent data
        data = get_cached_data('non_existent_key')
        self.assertIsNone(data)

    def test_set_cached_data(self):
        """Test set_cached_data function"""
        # Set data with function
        set_cached_data('test_key', 'test_value', 60)

        # Get data directly from cache
        data = cache.get('test_key')
        self.assertEqual(data, 'test_value')

class RateLimitDecoratorTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        # Setup request factory
        self.factory = RequestFactory()

        # Clear cache
        cache.clear()

    def test_rate_limit_under_limit(self):
        """Test rate limit decorator when under limit"""
        # Define test view
        @rate_limit('test_view', max_requests=5, timeout=60)
        def test_view(request):
            return "success"

        # Create request with user
        request = self.factory.get('/test-url/')
        request.user = self.user

        # Call view multiple times
        for _ in range(5):
            result = test_view(request)
            self.assertEqual(result, "success")

    def test_rate_limit_over_limit(self):
        """Test rate limit decorator when over limit"""
        # Define test view
        @rate_limit('test_view', max_requests=2, timeout=60)
        def test_view(request):
            return "success"

        # Create request with user
        request = self.factory.get('/test-url/')
        request.user = self.user

        # Call view up to limit
        for _ in range(2):
            result = test_view(request)
            self.assertEqual(result, "success")

        # Next call should be rate limited
        with patch('dashboard.decorators.JsonResponse') as mock_json_response:
            mock_response = MagicMock()
            mock_json_response.return_value = mock_response

            result = test_view(request)

            # Should return JsonResponse
            self.assertEqual(result, mock_response)

            # Verify JsonResponse was called with rate limit message
            call_args = mock_json_response.call_args[0][0]
            self.assertFalse(call_args['success'])
            self.assertIn('rate limit', call_args['error'].lower())