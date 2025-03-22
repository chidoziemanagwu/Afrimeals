from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.utils import timezone

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        # Clear session and redirect to home
        request.session.flush()
        messages.error(request, "Authentication failed. Please try again.")
        raise ImmediateHttpResponse(redirect('home'))  # Force immediate redirect

    def get_app(self, request, provider, client_id=None):
        try:
            return super().get_app(request, provider, client_id)
        except Exception as e:
            messages.error(request, "Authentication configuration error")
            raise ImmediateHttpResponse(redirect('home'))

    def pre_social_login(self, request, sociallogin):
        """Handle pre-login failures"""
        try:
            return super().pre_social_login(request, sociallogin)
        except Exception:
            # If there's an error, redirect to home
            if hasattr(request, 'session'):
                request.session.flush()
            messages.error(request, "Authentication failed. Please try again.")
            raise ImmediateHttpResponse(HttpResponseRedirect('/'))

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """Handle login redirect"""
        next_url = request.GET.get('next')
        return next_url if next_url else reverse('dashboard')

    def login(self, request, user):
        """Handle login process"""
        try:
            # Ensure clean session
            if hasattr(request, 'session'):
                request.session.cycle_key()
            return super().login(request, user)
        except Exception:
            if hasattr(request, 'session'):
                request.session.flush()
            messages.error(request, "Login failed. Please try again.")
            return HttpResponseRedirect('/')