# dashboard/adapters.py
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_logout_redirect_url(self, request):
        return '/'  # or reverse('home')