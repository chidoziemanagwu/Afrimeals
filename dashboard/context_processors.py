# dashboard/context_processors.py
from django.utils import timezone
from .models import UserSubscription

def subscription_status(request):
    if request.user.is_authenticated:
        subscription = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            end_date__gt=timezone.now()
        ).select_related('subscription_tier').first()
        return {
            'subscription': subscription,
            'has_subscription': subscription is not None
        }
    return {
        'subscription': None,
        'has_subscription': False
    }