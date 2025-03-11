# dashboard/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import UserActivity

@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        action='login',
        details={'ip': request.META.get('REMOTE_ADDR', '')}
    )

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    if user:
        UserActivity.objects.create(
            user=user,
            action='logout',
            details={'ip': request.META.get('REMOTE_ADDR', '')}
        )