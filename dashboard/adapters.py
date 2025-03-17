# dashboard/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_logout_redirect_url(self, request):
        """Redirect to home page after logout"""
        return '/'

    def get_login_redirect_url(self, request):
        """Handle post-login redirect"""
        next_url = request.GET.get('next', '')
        if next_url:
            return next_url
        return reverse('dashboard')  # or whatever your dashboard URL name is

    def login(self, request, user):
        """Handle login without causing redirect loop"""
        # Only redirect to Google if it's not already a Google login callback
        if not request.path.startswith('/accounts/google/login/callback/'):
            next_url = request.GET.get('next', '')
            return redirect(f'/accounts/google/login/?next={next_url}')
        # Otherwise, let the normal login process continue
        return super().login(request, user)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def get_connect_redirect_url(self, request, socialaccount):
        """Handle social account connection redirect"""
        return reverse('dashboard')  # or whatever your dashboard URL name is